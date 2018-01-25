#/usr/bin/env python3

import json
import uuid
import hashlib
import glob
import os
import xml.etree.ElementTree
from xml.etree import ElementTree
from xml.etree.ElementTree import (
    Element, SubElement, Comment, tostring,
)
from xml.dom import minidom

extra_components = ['MainExecutable', 'ProgramMenuDir']

def prettify(elem):
    """Return a pretty-printed XML string for the Element.
    """
    rough_string = ElementTree.tostring(elem, 'utf-8')
    reparsed = minidom.parseString(rough_string)
    return reparsed.toprettyxml(indent='  ')

def get_hash(path):
    hash_md5 = hashlib.md5()
    hash_md5.update(path.encode('utf-8'))
    return hash_md5.hexdigest()

def do_add_dependencies(dep, directory, component, relpath):
    pattern = dep['pattern']
    recurse = 'recurse' in dep and dep['recurse'] == 'yes'
    dir = dep['dir']
    preserve = 'preserve-hierarchy' in dep and  dep['preserve-hierarchy'] == 'yes'

    if dir[0] == '.': # Relative
        if dir == '.':
            src_dir = project['program']['dir']
        elif dir.startswith('.\\'):
            src_dir = project['program']['dir'] + '\\' + dir[2:]
        else:
            src_dir = project['program']['dir'] + '\\' + dir
    else: # Absolute
        src_dir = dir

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
                        'Guid' : component_info['Guid']
                    })

                    extra_components.append(component_info['Id'])
                else:
                    current_component = component

                SubElement(current_component, 'File', {
                    'Id' : 'File_' + get_hash(src_path),
                    'Name' : file_name,
                    'DiskId' : '1',
                    'Source' :  src_path,
                    'KeyPath' : 'yes' if preserve else 'no'
                })

            if os.path.isdir(src_path) and recurse:
                do_add_dependencies(dep, directory, component, relpath)

def add_dependencies(directory, component):
    for d in project['program']['dependencies']:
        do_add_dependencies(d, directory, component, '')


project_file = 'whid-setup'

with open(project_file + '.json', 'r') as f:
    project = json.load(f)

if not 'id' in project:
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
    #'Comments' : '',
    'InstallerVersion': '100',
    'Languages' : project['language'],
    'Compressed' : 'yes',
    'SummaryCodepage' : project['codepage']
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
    'Id' : 'ProgramFilesFolder',
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
    'Guid' : project['component-id']
})

exepath = project['program']['dir'] + '\\' + project['program']['binary']

wix_executable_file = SubElement(wix_component_main, 'File ', {
    'Id' : 'MainExecutableFile',
    'Name' : project['program']['binary'],
    'DiskId' : '1',
    'Source' :  exepath,
    'KeyPath' : 'yes'
})

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
        'Id' : 'startmenu',
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

SubElement(wix_rf_component, 'RegistryValue ', {
    'Root' : 'HKCU',
    'Key' : 'Software\[Manufacturer]\[ProductName]',
    'Type' : 'string',
    'Value' : '',
    'KeyPath' : 'yes' 
    })

SubElement(wix_product, 'Icon ', {
   'Id' :  project['program']['icon'],
   'SourceFile' :  project['program']['dir'] + '\\' + project['program']['icon']
})

add_dependencies(wix_installdir, wix_component_main)

wix_feature = SubElement(wix_product, 'Feature', {
    'Id' : 'Complete',
    'Level' : '1'
})

for id in extra_components:
    SubElement(wix_feature, 'ComponentRef', {
        'Id' : id
    })


with open(project_file + '.wxs', 'w') as f:
    print(prettify(wix_root))
    f.write(prettify(wix_root))

with open(project_file + '.json', 'w') as f:
     f.write(json.dumps(project, sort_keys=True, indent=4))
