#/usr/bin/env python3

import argparse
import json
import uuid
import hashlib
import glob
import os, sys
import subprocess
from ctypes import windll, POINTER
from ctypes.wintypes import LPWSTR, DWORD, BOOL
import xml.etree.ElementTree
from xml.etree import ElementTree
from xml.etree.ElementTree import (
    Element, SubElement, Comment, tostring,
)
from xml.dom import minidom

parser = argparse.ArgumentParser(description='Create a Windows Installer .msi file')

parser.add_argument('project', 
    help='Name of the project, without file extention')
parser.add_argument('--auto-create',
    choices=['simple', 'qt'],
    help='Create a project-file if required (Required extra arguments should be present)')
parser.add_argument('--project-name', help='Project name')
parser.add_argument('--executable', help='The main .exe file')
parser.add_argument('--project-version', help='Version of the project (n.n.n)')
parser.add_argument('--manufacturer', help='Manufacturer of the project (Person or company name)')
parser.add_argument('--version', help='Version of the project (n.n.n)')
parser.add_argument('--description', help='Description of the application')
parser.add_argument('--source-dir', help='The root-directory with the files to package')
parser.add_argument('--icon', help='Name of the icon file to use')
parser.add_argument('--add-desktop-shortcut', help='Add a desktop shortcut', action='store_true',)
parser.add_argument('--license', help='The license to use. This must be a text-file in .rtf format.')
parser.add_argument('--full-upgrade', 
    action='store_true',
    help='Make sure the application is reinstalled if it is previously installed')
parser.add_argument('--wix-root', help='The location where the WiX toolset is installed')
parser.add_argument('--wix-ui', help='WiX UI flavor to use', 
    choices=['WixUI_Mondo', 'WixUI_FeatureTree', 'WixUI_InstallDir', 'WixUI_Minimal', 'WixUI_Advanced'])
parser.add_argument('--wix-banner', help='Bitmap-file (.bmp) with a banner to show in the installer')
parser.add_argument('--merge-module',  help='Add a merge module (like a VC runtime)', action='append')
args = parser.parse_args()
if not args.project_name:
    args.project_name = args.project

project_file = args.project
wxs_file =  project_file + '.wxs'
msi_file = project_file + '.msi' 
wixobj_file = project_file + '.wixobj'
json_file = project_file + '.json'
project = {}
wix_path = ''

for f in [wxs_file, msi_file, wixobj_file]:
    if os.path.isfile(f):
        os.remove(f)

extra_components = ['MainExecutable', 'ProgramMenuDir']

def prettify(elem):
    rough_string = ElementTree.tostring(elem, 'utf-8')
    reparsed = minidom.parseString(rough_string)
    return reparsed.toprettyxml(indent='  ')

SCS_32BIT_BINARY = 0 # A 32-bit Windows-based application
SCS_64BIT_BINARY = 6 # A 64-bit Windows-based application
SCS_DOS_BINARY = 1 # An MS-DOS-based application
SCS_OS216_BINARY = 5 # A 16-bit OS/2-based application
SCS_PIF_BINARY = 3 # A PIF file that executes an MS-DOS-based application
SCS_POSIX_BINARY = 4 # A POSIX-based application
SCS_WOW_BINARY = 2 # A 16-bit Windows-based application

_GetBinaryType = windll.kernel32.GetBinaryTypeW
_GetBinaryType.argtypes = (LPWSTR, POINTER(DWORD))
_GetBinaryType.restype = BOOL

# https://stackoverflow.com/questions/1345632/determine-if-an-executable-or-library-is-32-or-64-bits-on-windows
def get_binary_type(filepath):
    res = DWORD(0)
    if _GetBinaryType(filepath, res) == 1:
        return res.value
    return None

def add_architecture(path, attr):
    type = get_binary_type(path)
    if type == SCS_64BIT_BINARY:
        attr['ProcessorArchitecture'] = 'x64'
    elif type == SCS_32BIT_BINARY:
        attr['ProcessorArchitecture'] = 'x32'
    return attr

def get_path(spec):
    if spec[0] == '.': # Relative
        if spec == '.':
            return project['program']['dir']
        if spec.startswith('.\\'):
            return project['program']['dir'] + '\\' + spec[2:]
        else:
            return project['program']['dir'] + '\\' + spec
    # Absolute
    return spec    

def get_hash(path):
    hash_md5 = hashlib.md5()
    hash_md5.update(path.encode('utf-8'))
    return hash_md5.hexdigest()

def do_add_dependencies(dep, dir, directory, component, relpath):
    pattern = dep['pattern']
    recurse = 'recurse' in dep and dep['recurse'] == 'yes'
    preserve = 'preserve-hierarchy' in dep and  dep['preserve-hierarchy'] == 'yes'
    src_dir = get_path(dir)

    for current_dir in glob.iglob(src_dir):
        if not os.path.isdir(current_dir):
            continue

        if (preserve):
            dir_hash = get_hash(current_dir)
            dir_name = os.path.basename(current_dir)
            current_relpath = relpath + '/' + dir
            current_directory = SubElement(directory, 'Directory', {
                'Id' : 'Dir' + dir_hash,
                'Name' : dir_name
            })
        else:
            current_directory = directory
            current_relpath = relpath

        for src_path in glob.iglob(current_dir + '\\' + pattern):

            file_name = os.path.basename(src_path)
            
            if os.path.isfile(src_path):

                if preserve:
                    # We need to remember the component-id
                    hash = get_hash(src_path)
                    if not 'generated-components' in project:
                        project['generated-components'] = {}
                    if hash in project['generated-components']:
                        component_info = project['generated-components'][hash]
                    else:
                        component_info = project['generated-components'][hash] = {
                            'Guid' : str(uuid.uuid4()),
                            'Id' : 'Generated_' + hash,
                            'Path' : src_path
                        }

                    current_component = SubElement(current_directory, 'Component', {
                        'Id' : component_info['Id'],
                        'Guid' : component_info['Guid'],
                        'Win64' : 'yes' if is_64_bit else 'no'
                    })

                    extra_components.append(component_info['Id'])
                else:
                    current_component = component

                SubElement(current_component, 'File', add_architecture(src_path, {
                    'Id' : 'File_' + get_hash(src_path),
                    'Name' : file_name,
                    'DiskId' : '1',
                    'Source' :  src_path,
                    'KeyPath' : 'yes' if preserve else 'no'
                    }))

            if os.path.isdir(src_path) and recurse:
                do_add_dependencies(dep, os.path.basename(src_path), directory, component, current_relpath)

def add_dependencies(directory, component):
    for d in project['program']['dependencies']:
        do_add_dependencies(d, d['dir'], directory, component, '')

def bootstrap():
    print('Bootstrapping project ' + args.project)
    # General stuff
    project['program'] = {}
    project['merge-modules'] = args.merge_module if args.merge_module else []
    project['manufacturer'] = args.manufacturer if args.manufacturer else "jgaa's Fan Club!"
    project['product'] = args.project_name
    project['version'] = args.project_version if args.project_version else '1.0.0'
    project['program']['dir'] = args.source_dir if args.source_dir else os.getcwd()
    project['program']['name'] = args.project_name
    # TODO: Try to search for an exe file if the guess is wrong
    project['program']['binary'] = args.executable if args.executable else args.project_name + '.exe'
    # TODO: Try to search for an icon file if the guess is wrong. If not found, use the exe
    project['program']['icon'] = args.icon if args.icon else args.project_name + '.ico'
    if args.license:
        project['program']['license'] = args.license
    project['program']['shortcuts'] = ['startmenu']
    project['program']['dependencies'] = [{
        'dir': '.',
        'pattern': '*.dll',
        'recurse': 'no'
    }]
    if args.add_desktop_shortcut:
        project['program']['shortcuts'].append('desktop')
    project['wix'] = {}
    if args.wix_ui:
        project['wix']['ui'] = args.wix_ui
    else:
        project['wix']['ui'] = 'WixUI_InstallDir'
    
    if args.wix_root:
        project['wix']['root-folder'] = args.wix_root

    if args.wix_banner:
        project['program']['banner'] = args.wix_banner

    # Add more specifics
    if args.auto_create == 'qt':
        # Add everything in subdirs
        project['program']['dependencies'].append({
            'dir': '.\\*',
            'pattern': '*',
            'preserve-hierarchy': 'yes',
            'recurse': 'yes'
        })
    elif args.auto_create == 'simple':
            pass

if os.path.isfile(json_file):
    with open(json_file, 'r') as f:
        project = json.load(f)
elif args.auto_create:
    bootstrap()
else:
    print("No project file '" + json_file + ", and no --auto-create argument specified!")
    sys.exit(-1)

if args.wix_root:
    wix_path = args.wix_root
elif 'wix' in project and 'root-folder' in project['wix']:
    wix_path = project['wix']['root-folder']

if wix_path and not wix_path.endswith('\\'):
    wix_path += '\\'
wix_path += 'bin\\'

# Handle update logic
# Basically, enforce a full update if the version has changed
if args.project_version:
    if project['version'] != args.project_version:
        args.full_upgrade = True
        project['version'] = args.project_version
        print('Resetting product-id')

if args.full_upgrade or not 'id' in project:
    project['id'] = str(uuid.uuid4())

if not 'upgrade-code' in project:
    project['upgrade-code'] = str(uuid.uuid4())

if not 'component-id' in project:
    project['component-id'] = str(uuid.uuid4())

if not 'rf-component-id' in project:
    project['rf-component-id'] = str(uuid.uuid4())

if not 'language' in project:
    project['language'] = '1033'

if not 'codepage' in project:
    project['codepage'] = '1252'

if not 'version' in project:
    project['version'] = '1.0.0'

exepath = project['program']['dir'] + '\\' + project['program']['binary']

# If the main application is 64 bit, assume that all binaries are 64 bits
# TODO: Support stand-alone 32 bit binaries as well as separate features(?)
is_64_bit = get_binary_type(exepath) == SCS_64BIT_BINARY

wix_root = Element('Wix', {'xmlns' : 'http://schemas.microsoft.com/wix/2006/wi'}) 

wix_product = SubElement(wix_root, 'Product', {
    'Name' : project['product'],
    'Manufacturer' : project['manufacturer'],
    'Id' : project['id'],
    'UpgradeCode' : project['upgrade-code'],
    'Language' :  project['language'],
    'Codepage' : project['codepage'],
    'Version' : project['version']
})

wix_package = SubElement(wix_product, 'Package ', {
    'Id' : '*',
    'Manufacturer' : project['manufacturer'],
    'Keywords' : 'Installer',
    'Description' : project['product'] + ' Installer',
    'InstallerVersion': '100',
    'Languages' : project['language'],
    'Compressed' : 'yes',
    'SummaryCodepage' : project['codepage'],
    'Platform': 'x64' if is_64_bit else 'x32'
})

SubElement(wix_product, 'Media  ', {
    'Id' : '1',
    'Cabinet' : 'mkmsi.cab',
    'EmbedCab' : 'yes'
})

wix_targetdir = SubElement(wix_product, 'Directory', {
    'Id' : 'TARGETDIR',
    'Name' : 'SourceDir'
})

wix_pfdir = SubElement(wix_targetdir, 'Directory', {
    'Id' :  'ProgramFiles64Folder' if is_64_bit else 'ProgramFilesFolder',
    'Name' : 'PFiles'
})

wix_companydir = SubElement(wix_pfdir, 'Directory', {
    'Id' : 'OrgDir',
    'Name' : project['manufacturer']
})

wix_installdir = SubElement(wix_companydir, 'Directory', {
    'Id' : 'INSTALLDIR',
    'Name' : project['product']
})

wix_component_main = SubElement(wix_installdir, 'Component ', {
    'Id' : 'MainExecutable',
    'Guid' : project['component-id'],
    'Win64' : 'yes' if is_64_bit else 'no'
})

wix_executable_file = SubElement(wix_component_main, 'File ', add_architecture(exepath, {
    'Id' : 'MainExecutableFile',
    'Name' : project['program']['binary'],
    'DiskId' : '1',
    'Source' :  exepath,
    'KeyPath' : 'yes',
    'Vital' : 'yes'
}))

if 'startmenu' in project['program']['shortcuts']:
    SubElement(wix_executable_file, 'Shortcut ', {
        'Id' : 'startmenu',
        'Directory' : 'ProgramMenuDir',
        'Name' : project['product'],
        'WorkingDirectory' : 'INSTALLDIR',
        'Icon' : project['program']['icon'], 
        'IconIndex' : '0',
        'Advertise' : 'yes'
    })

if 'desktop' in project['program']['shortcuts']:
    SubElement(wix_executable_file, 'Shortcut ', {
        'Id' : 'desktopshortcut',
        'Directory' : 'DesktopFolder',
        'Name' : project['product'],
        'WorkingDirectory' : 'INSTALLDIR',
        'Icon' : project['program']['icon'], 
        'IconIndex' : '0',
        'Advertise' : 'yes'
    })

wix_rf_component = SubElement(
    SubElement(
        SubElement(wix_targetdir, 'Directory', {
            'Id' : 'ProgramMenuFolder',
            'Name' : 'Programs'
        }),  'Directory', {
        'Id' : 'ProgramMenuDir',
        'Name' :  project['product']
    }), 'Component ', {
    'Id' : 'ProgramMenuDir',
    'Guid' : project['rf-component-id']})

SubElement(wix_rf_component, 'RemoveFolder', {
    'Id' : 'ProgramMenuDir',
    'On' : 'uninstall'
     })

SubElement(wix_rf_component, 'RegistryValue', {
    'Root' : 'HKCU',
    'Key' : 'Software\\[Manufacturer]\\[ProductName]',
    'Type' : 'string',
    'Value' : '',
    'KeyPath' : 'yes' 
    })

SubElement(wix_product, 'Icon', {
   'Id' :  project['program']['icon'],
   'SourceFile' :  project['program']['dir'] + '\\' + project['program']['icon']
})

SubElement(wix_targetdir, 'Directory', {
    'Id' : 'DesktopFolder',
    'Name' : 'Desktop'
})

add_dependencies(wix_installdir, wix_component_main)

wix_feature = SubElement(wix_product, 'Feature', {
    'Id' : 'Complete',
    'Level' : '1',
    'Title' : project['product'],
    'Description' : 'The complete package.',
    'Display' : 'expand',
    'ConfigurableDirectory' : 'INSTALLDIR'
})

wix_feature_product = SubElement(wix_feature, 'Feature', {
    'Id' : 'MainProgram',
    'Level' : '1',
    'Title' : project['product'],
    'Description' : 'The application'
})

for id in extra_components:
    SubElement(wix_feature_product, 'ComponentRef', {
        'Id' : id
    })

SubElement(wix_product, 'Property', {
    'Id' : 'WIXUI_INSTALLDIR',
    'Value' : 'INSTALLDIR'
    })


wix_ui = SubElement(wix_product, 'UI')
SubElement(wix_ui, 'UIRef', {
    'Id' : project['wix']['ui']
    })

SubElement(wix_product, 'UIRef', {
    'Id' : 'WixUI_ErrorProgressText'
    })

if project['program']['license']:
    SubElement(wix_product, 'WixVariable', {
        'Id' : 'WixUILicenseRtf',
        'Value' : get_path(project['program']['license'])
    })

if 'banner' in project['program']:
    SubElement(wix_product, 'WixVariable', {
        'Id' : 'WixUIBannerBmp',
        'Value' : project['program']['banner']
    })

wix_upgrade = SubElement(wix_product, 'Upgrade', {
   'Id' :  project['upgrade-code']
})

SubElement(wix_upgrade, 'UpgradeVersion', {
    'OnlyDetect' : 'yes',
    'Property' : 'NEWERFOUND',
    'Minimum' : project['version'].split('.')[0] + '.0.0',
    'IncludeMinimum' : 'no'
})

SubElement(wix_product, 'CustomAction', {
    'Id' : 'NoDowngrade',
    'Error' : 'A later version of [ProductName] is already installed.'
})

SubElement(SubElement(wix_product, 'InstallExecuteSequence'), 'Custom', {
    'Action' : 'NoDowngrade',
    'After' : 'FindRelatedProducts'
}).text='NEWERFOUND'

# Launch
SubElement(wix_product, 'Property', {
    'Id' : 'WIXUI_EXITDIALOGOPTIONALCHECKBOXTEXT',
    'Value' : 'Launch ' + project['program']['name']
})

SubElement(wix_product, 'Property', {
    'Id' : 'WixShellExecTarget',
    # Broken!
    #'Value' : '[#' + project['program']['binary'] + ']'
    'Value' : '[INSTALLDIR]\\' + project['program']['binary']
})

SubElement(wix_product, 'CustomAction', {
    'Id' : 'LaunchApplication',
    'BinaryKey': 'WixCA',
    'DllEntry': 'WixShellExec',
    'Impersonate': 'yes'
})

SubElement(wix_ui, 'Publish ', {
    'Dialog' : 'ExitDialog',
    'Control' : 'Finish',
    'Event' : 'DoAction',
    'Value' : 'LaunchApplication'
}).text = 'WIXUI_EXITDIALOGOPTIONALCHECKBOX = 1 and NOT Installed'

# End launch

for mm in project['merge-modules']:
    id = 'Merge_' + get_hash(mm)
    SubElement(SubElement(wix_product, 'DirectoryRef', {
            'Id' : 'TARGETDIR'
            }), 'Merge', {
        'Id' : id,
        'SourceFile' : mm,
        'DiskId' : '1',
        'Language' : '0'
    })
    SubElement(SubElement(wix_feature, 'Feature', {
        'Id' : id,
        'Title': "Merge module",
        'AllowAdvertise' : 'no',
        'Display' : 'hidden',
        'Level' : '1'
        }), 'MergeRef', {'Id' : id})


with open(wxs_file, 'w') as f:
    print(prettify(wix_root))
    f.write(prettify(wix_root))

with open(project_file + '.json', 'w') as f:
     f.write(json.dumps(project, sort_keys=True, indent=4))

candle = wix_path + 'candle'
print('Executing: ' + candle)
result = subprocess.run([candle, wxs_file])
if result.returncode != 0:
    print("Candle.exe failed with error: " + str(result.returncode))
    sys.exit(-1)

light = wix_path + 'light'
print('Executing: ' + light)
result = subprocess.run([light, '-ext', 'WixUIExtension', '-ext', 'WixUtilExtension.dll',  wixobj_file])
if result.returncode != 0:
    print("Light.exe failed with error: " + str(result.returncode))
    sys.exit(-1)

print("Done")
