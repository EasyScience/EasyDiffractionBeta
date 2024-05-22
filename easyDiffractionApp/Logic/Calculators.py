# SPDX-FileCopyrightText: 2023 EasyDiffraction contributors
# SPDX-License-Identifier: BSD-3-Clause
# © 2023 Contributors to the EasyDiffraction project <https://github.com/easyscience/EasyDiffraction>

import numpy as np
from pycifstar.global_ import Global

from EasyApp.Logic.Logging import console
from Logic.Helpers import IO

try:
    import cryspy
    from cryspy.H_functions_global.function_1_cryspy_objects import \
        str_to_globaln
    from cryspy.A_functions_base.function_2_space_group import \
        get_it_coordinate_system_codes_by_it_number
    console.debug('CrysPy module imported')
except ImportError:
    console.error('No CrysPy module found')


class Parameter(dict):

    def __init__(self,
                value,
                permittedValues = None,
                idx = 0,
                error = 0.0,
                min = -np.inf,
                max = np.inf,
                absDelta = None,
                pctDelta = None,
                units = '',
                category = '',
                prettyCategory = '',
                rowName = '',
                name = '',
                prettyName = '',
                shortPrettyName = '',
                icon = '',
                categoryIcon = '',
                url = '',
                cifDict = '',
                optional = False,
                enabled = True,
                fittable = False,
                fit = False):
        self['value'] = value
        self['permittedValues'] = permittedValues
        self['idx'] = idx
        self['optional'] = optional
        self['enabled'] = enabled
        self['fittable'] = fittable
        self['fit'] = fit
        self['error'] = error
        self['group'] = ""
        self['min'] = min
        self['max'] = max
        self['absDelta'] = absDelta
        self['pctDelta'] = pctDelta
        self['category'] = category
        self['prettyCategory'] = prettyCategory
        self['rowName'] = rowName
        self['name'] = name
        self['prettyName'] = prettyName
        self['shortPrettyName'] = shortPrettyName
        self['icon'] = icon
        self['categoryIcon'] = categoryIcon
        self['url'] = url
        self['cifDict'] = cifDict
        self['parentIndex'] = 0
        self['parentName'] = ''
        self['units'] = units


class CryspyParser:

    @staticmethod
    def cifToDict(cif):
        obj = Global()
        obj.take_from_string(cif)
        data = obj.datas[0]
        out = {'name': data.name, 'items': {}, 'loops': {}}
        for item in data.items.items:
            out['items'][item.name] = item.value
        for loop in data.loops:
            category = loop.prefix
            out['loops'][category] = {}
            for paramIdx, fullParamName in enumerate(loop.names):
                paramName = fullParamName.replace(category, '')
                paramValues = [values[paramIdx] for values in loop.values]
                out['loops'][category][paramName] = paramValues
        return out

    @staticmethod
    def dataBlocksToCif(blocks):
        cif = ''
        for block in blocks:
            cif += CryspyParser.dataBlockToCif(block) + '\n\n'
        return cif

    @staticmethod
    def dataBlockToCif(block, includeBlockName=True):
        cif = ''

        if includeBlockName:
            cif += f"data_{block['name']['value']}"
            cif += '\n\n'

        if 'params' in block:
            for category in block['params'].values():
                for param in category.values():
                    if param["optional"]:
                        continue

                    value = param["value"]
                    if value is None:
                        continue

                    if isinstance(value, (float, int)):  # If parameter is of float type
                        value = np.float32(value)  # Simplifies output
                        if param["fit"]:
                            error = param["error"]
                            #error = np.float32(error)  # Simplifies output
                            if error == 0:
                                paramStr = f'{value}()' # Adds empty brackets for standard uncertainty for free params
                            else:
                                _, _, paramStr = IO.toStdDevSmalestPrecision(value, error) # Adds brackets with standard uncertainty for free params
                        else:
                            paramStr = str(value)  # Keeps 32bit presicion format in contrast to f'{...}'
                    elif isinstance(value, str):  # If parameter is of string type
                        if ' ' in value:  # Adds quotes to text with spaces, e.g. P n m a -> "P n m a"
                            paramStr = f'"{value}"'
                        else:
                            paramStr = f'{value}'
                    else:
                        console.error(f'Unsupported parameter type {type(value)} for {value}')
                        continue

                    cif += f'{param["category"]}.{param["name"]} {paramStr}'
                    cif += '\n'
                cif += '\n'

        if 'loops' in block:
            for categoryName, category in block['loops'].items():
                cif += '\nloop_\n'

                # loop header
                row0 = category[0]
                for param in row0.values():
                    if param["optional"]:
                        continue
                    cif += f'{categoryName}.{param["name"]}\n'

                # loop data
                for row in category:
                    line = ''
                    for param in row.values():
                        if param["optional"]:
                            continue

                        value = param["value"]
                        if value is None:
                            continue

                        if isinstance(value, (float, int)):  # If parameter is number
                            value = np.float32(value)  # Simplifies output
                            if param["fit"]:
                                error = param["error"]
                                #error = np.float32(error)  # Simplifies output
                                if error == 0:
                                    paramStr = f'{value}()' # Adds empty brackets for standard uncertainty for free params
                                else:
                                    _, _, paramStr = IO.toStdDevSmalestPrecision(value, error) # Adds brackets with standard uncertainty for free params
                            else:
                                paramStr = str(value)  # Keeps 32bit presicion format in contrast to f'{...}'
                        elif isinstance(value, str):  # If parameter is of string type
                            if ' ' in value:  # Adds quotes to text with spaces, e.g. P n m a -> "P n m a"
                                paramStr = f'"{value}"'
                            else:
                                paramStr = f'{value}'
                        else:
                            console.error(f'Unsupported parameter type {type(value)} for {value}')
                            continue

                        line += paramStr + ' '
                    line = line.rstrip()
                    cif += f'{line}\n'
        cif = cif.strip()
        cif = cif.replace('\n\n\n', '\n\n')
        return cif

    @staticmethod
    def edCifToCryspyCif(edCif, diffrn_radiation_type='cw'):
        rawToEdNamesCif = {
            '_symmetry_space_group_name_H-M': '_space_group.name_H-M_alt',
            '_atom_site_thermal_displace_type': '_atom_site.ADP_type',
            '_atom_site_adp_type': '_atom_site.ADP_type',
            '_atom_site_U_iso_or_equiv': '_atom_site.U_iso_or_equiv'
        }
        edToCryspyNamesMap = {}
        edToCryspyNamesMap['base'] = {
            '_atom_site.site_symmetry_multiplicity': '_atom_site_multiplicity',

            '_diffrn_radiation.probe': '_setup_radiation',

            '_pd_phase_block.id': '_phase_label',
            '_pd_phase_block.scale': '_phase_scale',

            '_model.cif_file_name': '_model_cif_file_name',
            '_experiment.cif_file_name': '_experiment_cif_file_name'
        }
        edToCryspyNamesMap['cw'] = {
            '_diffrn_radiation_wavelength.wavelength': '_setup_wavelength',

            '_pd_calib.2theta_offset': '_setup_offset_2theta',

            '_pd_instr.resolution_u': '_pd_instr_resolution_u',
            '_pd_instr.resolution_v': '_pd_instr_resolution_v',
            '_pd_instr.resolution_w': '_pd_instr_resolution_w',
            '_pd_instr.resolution_x': '_pd_instr_resolution_x',
            '_pd_instr.resolution_y': '_pd_instr_resolution_y',

            '_pd_instr.reflex_asymmetry_p1': '_pd_instr_reflex_asymmetry_p1',
            '_pd_instr.reflex_asymmetry_p2': '_pd_instr_reflex_asymmetry_p2',
            '_pd_instr.reflex_asymmetry_p3': '_pd_instr_reflex_asymmetry_p3',
            '_pd_instr.reflex_asymmetry_p4': '_pd_instr_reflex_asymmetry_p4',

            '_pd_meas.2theta_scan': '_pd_meas_2theta',
            '_pd_meas.intensity_total_su': '_pd_meas_intensity_sigma',  # before _pd_meas.intensity_total!
            '_pd_meas.intensity_total': '_pd_meas_intensity',

            # NEED see if we can hide this as for TOF case
            '_pd_meas.2theta_range_min': '_range_2theta_min',
            '_pd_meas.2theta_range_max': '_range_2theta_max',

            # NEED to remove this and use our handling of a background as for TOF case
            '_pd_background.line_segment_X': '_pd_background_2theta',
            '_pd_background.line_segment_intensity': '_pd_background_intensity',
        }
        edToCryspyNamesMap['tof'] = {
            '_pd_instr.zero': '_tof_parameters_Zero',
            '_pd_instr.dtt1': '_tof_parameters_Dtt1',
            '_pd_instr.dtt2': '_tof_parameters_dtt2',
            '_pd_instr.2theta_bank': '_tof_parameters_2theta_bank',

            '_pd_instr.peak_shape': '_tof_profile_peak_shape',
            '_pd_instr.alpha0': '_tof_profile_alpha0',
            '_pd_instr.alpha1': '_tof_profile_alpha1',
            '_pd_instr.beta0':  '_tof_profile_beta0',
            '_pd_instr.beta1':  '_tof_profile_beta1',
            '_pd_instr.gamma0': '_tof_profile_gamma0',
            '_pd_instr.gamma1': '_tof_profile_gamma1',
            '_pd_instr.gamma2': '_tof_profile_gamma2',
            '_pd_instr.sigma0': '_tof_profile_sigma0',
            '_pd_instr.sigma1': '_tof_profile_sigma1',
            '_pd_instr.sigma2': '_tof_profile_sigma2',

            '_tof_background.time_max': '_tof_background_time_max',
            '_tof_background.coeff': '_tof_background_coeff',

            '_pd_meas.time_of_flight': '_tof_meas_time',
            '_pd_meas.intensity_total_su': '_tof_meas_intensity_sigma',  # before _pd_meas.intensity_total!
            '_pd_meas.intensity_total': '_tof_meas_intensity',

            '_pd_meas.tof_range_min': '_range_time_min',
            '_pd_meas.tof_range_max': '_range_time_max',
        }
        edToCryspyValuesMap = {
            'x-ray': 'X-rays',
            'neutron': 'neutrons',
            'neutronss': 'neutrons',
        }
        cryspyCif = edCif
        for rawName, edName in rawToEdNamesCif.items():
            cryspyCif = cryspyCif.replace(rawName, edName)
        for edName, cryspyName in edToCryspyNamesMap['base'].items():
            cryspyCif = cryspyCif.replace(edName, cryspyName)
        for edName, cryspyName in edToCryspyNamesMap[diffrn_radiation_type].items():
            cryspyCif = cryspyCif.replace(edName, cryspyName)
        for edValue, cryspyValue in edToCryspyValuesMap.items():
            cryspyCif = cryspyCif.replace(edValue, cryspyValue)
        return cryspyCif

    @staticmethod
    def cryspyCifToModelsObj(cryspyCif):
        cryspyModelsObj = str_to_globaln(cryspyCif)

        # Replace atom types
        for dataBlock in cryspyModelsObj.items:
            if type(dataBlock) is not cryspy.E_data_classes.cl_1_crystal.Crystal:
                continue
            for item in dataBlock.items:
                if type(item) is not cryspy.C_item_loop_classes.cl_1_atom_site.AtomSiteL:
                    continue
                for cryspy_atom in item.items:
                    if cryspy_atom.type_symbol == 'D':
                        cryspy_atom.type_symbol = '2H'
                    elif cryspy_atom.type_symbol == 'H1+':
                        cryspy_atom.type_symbol = 'H'

        return cryspyModelsObj

    @staticmethod
    def starObjToEdProject(starObj):
        edProject = {'name': '', 'params': {}, 'loops': {}}

        # DATABLOCK ID

        edProject['name'] = dict(Parameter(
            starObj.name,
            icon = 'archive',
            url = 'https://docs.easydiffraction.org/app/project/dictionaries/',
        ))

        # DATABLOCK SINGLES

        for param in starObj.items.items:
            if param.name == '_project.description':
                category, name = param.name.split('.')
                if category not in edProject['params']:
                    edProject['params'][category] = {}
                edProject['params'][category][name] = dict(Parameter(
                    param.value,
                    category = category,
                    name = name,
                    prettyName = 'Description',
                    url = 'https://docs.easydiffraction.org/app/project/dictionaries/',
                ))

        # DATABLOCK TABLES

        for loop in starObj.loops:
            category = loop.prefix

            if category == '_model_cif_file':
                edModels = []
                for rowIdx, rowItems in enumerate(loop.values):
                    edModel = {}
                    for columnIdx, columnName in enumerate(loop.names):
                        if columnName.replace('.', '_')  == '_model_cif_file_name':  # NEED FIX
                            edModel['cif_file_name'] = dict(Parameter(
                                rowItems[columnIdx],
                                category = '_model',
                                name = 'cif_file_name',
                                prettyName = 'Model file',
                                url = 'https://easydiffraction.org'
                            ))
                    edModels.append(edModel)
                edProject['loops']['_model'] = edModels

            elif category == '_experiment_cif_file':
                edExperiments = []
                for rowIdx, rowItems in enumerate(loop.values):
                    edExperiment = {}
                    for columnIdx, columnName in enumerate(loop.names):
                        if columnName.replace('.', '_') == '_experiment_cif_file_name':  # NEED FIX
                            edExperiment['cif_file_name'] = dict(Parameter(
                                rowItems[columnIdx],
                                category = '_experiment',
                                name = 'cif_file_name',
                                prettyName = 'Experiment file',
                                url = 'https://easydiffraction.org'
                            ))
                    edExperiments.append(edExperiment)
                edProject['loops']['_experiment'] = edExperiments

        return edProject

    @staticmethod
    def cryspyObjToEdModels(cryspy_obj):
        ed_phases = []

        for data_block in cryspy_obj.items:
            # Skip non-crystal data blocks

            if type(data_block) is not cryspy.E_data_classes.cl_1_crystal.Crystal:
                continue

            # If crystal data block found

            cryspy_phase = data_block.items
            ed_phase = {'name': '', 'params': {}, 'loops': {}}

            # DATABLOCK ID

            ed_phase['name'] = dict(Parameter(
                data_block.data_name.lower(),
                icon='layer-group',
                url='https://docs.easydiffraction.org/app/project/dictionaries/',
            ))

            for item in cryspy_phase:

                # DATABLOCK SINGLES

                # Space group category
                if type(item) is cryspy.C_item_loop_classes.cl_2_space_group.SpaceGroup:
                    if not '_space_group' in ed_phase['params']:
                        ed_phase['params']['_space_group'] = {}
                    ed_phase['params']['_space_group']['name_H-M_alt'] = dict(Parameter(
                        item.name_hm_alt,
                        category='_space_group',
                        name='name_H-M_alt',
                        shortPrettyName='name',
                        url='https://docs.easydiffraction.org/app/project/dictionaries/_space_group/',
                        cifDict='core'
                    ))
                    ed_phase['params']['_space_group']['IT_coordinate_system_code'] = dict(Parameter(
                        item.it_coordinate_system_code,
                        category='_space_group',
                        name='IT_coordinate_system_code',
                        shortPrettyName='code',
                        permittedValues=list(get_it_coordinate_system_codes_by_it_number(item.it_number)),
                        url='https://docs.easydiffraction.org/app/project/dictionaries/_space_group/',
                        cifDict='core'
                    ))
                    ed_phase['params']['_space_group']['crystal_system'] = dict(Parameter(
                        item.crystal_system,
                        optional=True,
                        category='_space_group',
                        name='crystal_system',
                        shortPrettyName='crystal system',
                        url='https://docs.easydiffraction.org/app/project/dictionaries/_space_group/',
                        cifDict='core'
                    ))
                    ed_phase['params']['_space_group']['IT_number'] = dict(Parameter(
                        item.it_number,
                        optional=True,
                        category='_space_group',
                        name='IT_number',
                        shortPrettyName='number',
                        url='https://docs.easydiffraction.org/app/project/dictionaries/_space_group/',
                        cifDict='core'
                    ))

                # Cell category
                elif type(item) is cryspy.C_item_loop_classes.cl_1_cell.Cell:
                    if not '_cell' in ed_phase['params']:
                        ed_phase['params']['_cell'] = {}
                    ed_phase['params']['_cell']['length_a'] = dict(Parameter(
                        item.length_a,
                        error=item.length_a_sigma,  # NEED FIX: rename 'error' to 'su'
                        category='_cell',
                        prettyCategory='cell',
                        name='length_a',
                        prettyName='length a',
                        shortPrettyName='a',  # NEED FIX: rename 'shortPrettyName' to 'shortName' ???
                        icon='ruler',
                        categoryIcon='cube',
                        url='https://docs.easydiffraction.org/app/project/dictionaries/_cell/',
                        cifDict='core',
                        enabled=not item.length_a_constraint,
                        absDelta=0.1,
                        units='Å',
                        fittable=True,
                        fit=item.length_a_refinement
                    ))
                    ed_phase['params']['_cell']['length_b'] = dict(Parameter(
                        item.length_b,
                        error=item.length_b_sigma,
                        category='_cell',
                        prettyCategory='cell',
                        name='length_b',
                        prettyName='length b',
                        shortPrettyName='b',
                        icon='ruler',
                        categoryIcon='cube',
                        url='https://docs.easydiffraction.org/app/project/dictionaries/_cell/',
                        cifDict='core',
                        enabled=not item.length_b_constraint,
                        absDelta=0.1,
                        units='Å',
                        fittable=True,
                        fit=item.length_b_refinement
                    ))
                    ed_phase['params']['_cell']['length_c'] = dict(Parameter(
                        item.length_c,
                        error=item.length_c_sigma,
                        category='_cell',
                        prettyCategory='cell',
                        name='length_c',
                        prettyName='length c',
                        shortPrettyName='c',
                        icon='ruler',
                        categoryIcon='cube',
                        url='https://docs.easydiffraction.org/app/project/dictionaries/_cell/',
                        cifDict='core',
                        enabled=not item.length_c_constraint,
                        absDelta=0.1,
                        units='Å',
                        fittable=True,
                        fit=item.length_c_refinement
                    ))
                    ed_phase['params']['_cell']['angle_alpha'] = dict(Parameter(
                        item.angle_alpha,
                        error=item.angle_alpha_sigma,
                        category='_cell',
                        prettyCategory='cell',
                        name='angle_alpha',
                        prettyName='angle α',
                        shortPrettyName='α',
                        icon='ruler',
                        categoryIcon='less-than',
                        url='https://docs.easydiffraction.org/app/project/dictionaries/_cell/',
                        cifDict='core',
                        enabled=not item.angle_alpha_constraint,
                        absDelta=1.0,
                        units='°',
                        fittable=True,
                        fit=item.angle_alpha_refinement
                    ))
                    ed_phase['params']['_cell']['angle_beta'] = dict(Parameter(
                        item.angle_beta,
                        error=item.angle_beta_sigma,
                        category='_cell',
                        prettyCategory='cell',
                        name='angle_beta',
                        prettyName='angle β',
                        shortPrettyName='β',
                        icon='ruler',
                        categoryIcon='less-than',
                        url='https://docs.easydiffraction.org/app/project/dictionaries/_cell/',
                        cifDict='core',
                        enabled=not item.angle_beta_constraint,
                        absDelta=1.0,
                        units='°',
                        fittable=True,
                        fit=item.angle_beta_refinement
                    ))
                    ed_phase['params']['_cell']['angle_gamma'] = dict(Parameter(
                        item.angle_gamma,
                        error=item.angle_gamma_sigma,
                        category='_cell',
                        prettyCategory='cell',
                        name='angle_gamma',
                        prettyName='angle γ',
                        shortPrettyName='γ',
                        icon='ruler',
                        categoryIcon='less-than',
                        url='https://docs.easydiffraction.org/app/project/dictionaries/_cell/',
                        cifDict='core',
                        enabled=not item.angle_gamma_constraint,
                        absDelta=1.0,
                        units='°',
                        fittable=True,
                        fit=item.angle_gamma_refinement
                    ))

                # DATABLOCK TABLES

                # Atom site category
                elif type(item) is cryspy.C_item_loop_classes.cl_1_atom_site.AtomSiteL:
                    cryspy_atoms = item.items
                    ed_atoms = []
                    for idx, cryspy_atom in enumerate(cryspy_atoms):
                        ed_atom = {}
                        ed_atom['label'] = dict(Parameter(
                            cryspy_atom.label,
                            idx=idx,
                            category='_atom_site',
                            name='label',
                            shortPrettyName='label',
                            url='https://docs.easydiffraction.org/app/project/dictionaries/_atom_site/',
                            cifDict='core'
                        ))
                        ed_atom['type_symbol'] = dict(Parameter(
                            cryspy_atom.type_symbol,
                            idx=idx,
                            category='_atom_site',
                            name='type_symbol',
                            shortPrettyName='type',
                            url='https://docs.easydiffraction.org/app/project/dictionaries/_atom_site/',
                            cifDict='core'
                        ))
                        ed_atom['fract_x'] = dict(Parameter(
                            cryspy_atom.fract_x,
                            error=cryspy_atom.fract_x_sigma,
                            idx=idx,
                            category='_atom_site',
                            prettyCategory='atom',
                            rowName=cryspy_atom.label,
                            name='fract_x',
                            prettyName='fract x',
                            shortPrettyName='x',
                            icon='map-marker-alt',
                            categoryIcon='atom',
                            url='https://docs.easydiffraction.org/app/project/dictionaries/_atom_site/',
                            cifDict='core',
                            enabled=not cryspy_atom.fract_x_constraint,
                            absDelta=0.05,
                            fittable=True,
                            fit=cryspy_atom.fract_x_refinement
                        ))
                        ed_atom['fract_y'] = dict(Parameter(
                            cryspy_atom.fract_y,
                            error=cryspy_atom.fract_y_sigma,
                            idx=idx,
                            category='_atom_site',
                            prettyCategory='atom',
                            rowName=cryspy_atom.label,
                            name='fract_y',
                            prettyName='fract y',
                            shortPrettyName='y',
                            icon='map-marker-alt',
                            categoryIcon='atom',
                            url='https://docs.easydiffraction.org/app/project/dictionaries/_atom_site/',
                            cifDict='core',
                            enabled=not cryspy_atom.fract_y_constraint,
                            absDelta=0.05,
                            fittable=True,
                            fit=cryspy_atom.fract_y_refinement
                        ))
                        ed_atom['fract_z'] = dict(Parameter(
                            cryspy_atom.fract_z,
                            error=cryspy_atom.fract_z_sigma,
                            idx=idx,
                            category='_atom_site',
                            prettyCategory='atom',
                            rowName=cryspy_atom.label,
                            name='fract_z',
                            prettyName='fract z',
                            shortPrettyName='z',
                            icon='map-marker-alt',
                            categoryIcon='atom',
                            url='https://docs.easydiffraction.org/app/project/dictionaries/_atom_site/',
                            cifDict='core',
                            enabled=not cryspy_atom.fract_z_constraint,
                            absDelta=0.05,
                            fittable=True,
                            fit=cryspy_atom.fract_z_refinement
                        ))
                        ed_atom['occupancy'] = dict(Parameter(
                            cryspy_atom.occupancy,
                            error=cryspy_atom.occupancy_sigma,
                            idx=idx,
                            category='_atom_site',
                            prettyCategory='atom',
                            rowName=cryspy_atom.label,
                            name='occupancy',
                            prettyName='occ',
                            shortPrettyName='occ',
                            icon='fill',
                            categoryIcon='atom',
                            url='https://docs.easydiffraction.org/app/project/dictionaries/_atom_site/',
                            cifDict='core',
                            enabled=not cryspy_atom.occupancy_constraint,
                            absDelta=0.05,
                            fittable=True,
                            fit=cryspy_atom.occupancy_refinement
                        ))
                        ed_atom['ADP_type'] = dict(Parameter(
                            'Biso',  # cryspy_atom.adp_type,
                            idx=idx,
                            category='_atom_site',
                            name='ADP_type',
                            shortPrettyName='type',
                            url='https://docs.easydiffraction.org/app/project/dictionaries/_atom_site/',
                            cifDict='core'
                        ))
                        b_iso_or_equiv = 0.0
                        b_iso_or_equiv_sigma = 0.0
                        if hasattr(cryspy_atom, 'b_iso_or_equiv'):
                            b_iso_or_equiv = cryspy_atom.b_iso_or_equiv
                            b_iso_or_equiv_sigma = cryspy_atom.b_iso_or_equiv_sigma
                        if hasattr(cryspy_atom, 'u_iso_or_equiv'):
                            b_iso_or_equiv = round(cryspy_atom.u_iso_or_equiv * 8 * np.pi ** 2, 4)
                            b_iso_or_equiv_sigma = round(cryspy_atom.u_iso_or_equiv_sigma * 8 * np.pi ** 2, 4)
                        ed_atom['B_iso_or_equiv'] = dict(Parameter(
                            b_iso_or_equiv,
                            error=b_iso_or_equiv_sigma,
                            idx=idx,
                            category='_atom_site',
                            prettyCategory='atom',
                            rowName=cryspy_atom.label,
                            name='B_iso_or_equiv',
                            prettyName='Biso',
                            shortPrettyName='iso',
                            icon='arrows-alt',
                            categoryIcon='atom',
                            url='https://docs.easydiffraction.org/app/project/dictionaries/_atom_site/',
                            cifDict='core',
                            enabled=not cryspy_atom.b_iso_or_equiv_constraint,
                            absDelta=0.1,
                            units='Å²',
                            fittable=True,
                            fit=cryspy_atom.b_iso_or_equiv_refinement
                        ))
                        ed_atom['site_symmetry_multiplicity'] = dict(Parameter(
                            cryspy_atom.multiplicity,
                            optional=True,
                            idx=idx,
                            category='_atom_site',
                            name='site_symmetry_multiplicity',
                            url='https://docs.easydiffraction.org/app/project/dictionaries/_atom_site/',
                            cifDict='core'
                        ))
                        ed_atom['Wyckoff_symbol'] = dict(Parameter(
                            cryspy_atom.wyckoff_symbol,
                            optional=True,
                            category='_atom_site',
                            name='Wyckoff_symbol',
                            url='https://docs.easydiffraction.org/app/project/dictionaries/_atom_site/',
                            cifDict='core'
                        ))
                        ed_atoms.append(ed_atom)
                    ed_phase['loops']['_atom_site'] = ed_atoms

            ed_phases.append(ed_phase)

        return ed_phases

    @staticmethod
    def cryspyObjAndDictToEdExperiments(cryspy_obj, cryspy_dict):  # NEED to be modified similar to cryspyObjAndDictToEdModels -> cryspyObjToEdModels

        experiment_names = []
        exp_substrings = ['pd_', 'tof_', 'data_']  # possible experiment prefixes
        # get experiment names from cryspy_dict
        for key in cryspy_dict.keys():
            for substring in exp_substrings:
                if key.startswith(substring):
                    key = key.replace(substring, "").replace("_", "")
                    experiment_names.append(key)

        ed_experiments_meas_only = []
        ed_experiments_no_meas = []

        for data_block in cryspy_obj.items:
            data_block_name = data_block.data_name

            if data_block_name in experiment_names:
                cryspy_experiment = data_block.items
                ed_experiment_no_meas = {'name': '', 'params': {}, 'loops': {}}
                ed_experiment_meas_only = {'name': '', 'loops': {}}

                # DATABLOCK ID

                ed_experiment_no_meas['name'] = dict(Parameter(
                    data_block_name,
                    icon = 'microscope',
                    url = 'https://docs.easydiffraction.org/app/project/dictionaries/',
                ))
                ed_experiment_meas_only['name'] = dict(Parameter(
                    data_block_name,
                    icon = 'microscope',
                    url = 'https://docs.easydiffraction.org/app/project/dictionaries/',
                ))

                for item in cryspy_experiment:

                    # DATABLOCK SINGLES

                    # Ranges category (CW)
                    if type(item) == cryspy.C_item_loop_classes.cl_1_range.Range:
                        ed_experiment_no_meas['params']['_pd_meas'] = {}
                        if hasattr(item, 'ttheta_min') and hasattr(item, 'ttheta_max'):
                            ed_experiment_no_meas['params']['_pd_meas']['2theta_range_min'] = dict(Parameter(
                                item.ttheta_min,
                                optional = True,
                                category = '_pd_meas',
                                name = '2theta_range_min',
                                prettyName = 'range min',
                                shortPrettyName = 'min',
                                url = 'https://docs.easydiffraction.org/app/project/dictionaries/',
                                cifDict = 'pd'
                            ))
                            ed_experiment_no_meas['params']['_pd_meas']['2theta_range_max'] = dict(Parameter(
                                item.ttheta_max,
                                optional = True,
                                category = '_pd_meas',
                                name = '2theta_range_max',
                                prettyName = 'range max',
                                shortPrettyName = 'max',
                                url = 'https://docs.easydiffraction.org/app/project/dictionaries/',
                                cifDict = 'pd'
                            ))
                            ed_experiment_no_meas['params']['_pd_meas']['2theta_range_inc'] = dict(Parameter(
                                0.1,  # initial value to be updated later
                                optional = True,
                                category = '_pd_meas',
                                name = '2theta_range_inc',
                                prettyName = 'range inc',
                                shortPrettyName = 'inc',
                                url = 'https://docs.easydiffraction.org/app/project/dictionaries/',
                                cifDict = 'pd'
                            ))
                        # Ranges category (TOF)
                        elif hasattr(item, 'time_min') and hasattr(item, 'time_max'):
                            ed_experiment_no_meas['params']['_pd_meas']['tof_range_min'] = dict(Parameter(
                                item.time_min,
                                optional = True,
                                category = '_pd_meas',
                                name = 'tof_range_min',
                                prettyName = 'range min',
                                shortPrettyName = 'min',
                                url = 'https://docs.easydiffraction.org/app/project/dictionaries/'
                            ))
                            ed_experiment_no_meas['params']['_pd_meas']['tof_range_max'] = dict(Parameter(
                                item.time_max,
                                optional = True,
                                category = '_pd_meas',
                                name = 'tof_range_max',
                                prettyName = 'range max',
                                shortPrettyName = 'max',
                                url = 'https://docs.easydiffraction.org/app/project/dictionaries/'
                            ))
                            ed_experiment_no_meas['params']['_pd_meas']['tof_range_inc'] = dict(Parameter(
                                10.0,  # initial value to be updated later
                                optional = True,
                                category = '_pd_meas',
                                name = 'tof_range_inc',
                                prettyName = 'range inc',
                                shortPrettyName = 'inc',
                                url = 'https://docs.easydiffraction.org/app/project/dictionaries/'
                            ))

                # Start from the beginning after reading ranges
                for item in cryspy_experiment:

                    # DATABLOCK SINGLES

                    # Phases section
                    if type(item) is cryspy.C_item_loop_classes.cl_1_phase.PhaseL:
                        cryspy_phases = item.items
                        ed_phases = []
                        for idx, cryspy_phase in enumerate(cryspy_phases):
                            ed_phase = {}
                            ed_phase['id'] = dict(Parameter(
                                cryspy_phase.label,
                                idx = idx,
                                category = '_pd_phase_block',
                                name = 'id',
                                shortPrettyName = 'label',
                                url = 'https://docs.easydiffraction.org/app/project/dictionaries/_phase/',
                                cifDict = 'pd'
                            ))
                            ed_phase['scale'] = dict(Parameter(
                                cryspy_phase.scale,
                                error = cryspy_phase.scale_sigma,
                                idx = idx,
                                category = '_pd_phase_block',
                                prettyCategory = 'phase',
                                rowName = cryspy_phase.label,
                                name = 'scale',
                                prettyName = 'scale',
                                shortPrettyName = 'scale',
                                icon = 'weight',
                                categoryIcon = 'layer-group',
                                url = 'https://docs.easydiffraction.org/app/project/dictionaries/_phase/',
                                cifDict = 'pd',
                                pctDelta = 25,
                                fittable = True,
                                fit = cryspy_phase.scale_refinement
                            ))
                            ed_phases.append(ed_phase)
                        ed_experiment_no_meas['loops']['_pd_phase_block'] = ed_phases

                    # Cryspy setup section (TOF/CW)
                    elif type(item) == cryspy.C_item_loop_classes.cl_1_setup.Setup:
                        if hasattr(item, 'radiation'):
                            if not '_diffrn_radiation' in ed_experiment_no_meas['params']:
                                ed_experiment_no_meas['params']['_diffrn_radiation'] = {}
                            ed_experiment_no_meas['params']['_diffrn_radiation']['probe'] = dict(Parameter(
                                item.radiation.replace('neutrons', 'neutron').replace('X-rays', 'x-ray'),  # NEED FIX
                                permittedValues = ['neutron', 'x-ray'],
                                category = '_diffrn_radiation',
                                name = 'probe',
                                shortPrettyName = 'probe',
                                url = 'https://docs.easydiffraction.org/app/project/dictionaries/_diffrn_radiation/',
                                cifDict = 'core'
                            ))
                        if hasattr(item, 'wavelength'):
                            if not '_diffrn_radiation_wavelength' in ed_experiment_no_meas['params']:
                                ed_experiment_no_meas['params']['_diffrn_radiation_wavelength'] = {}
                            ed_experiment_no_meas['params']['_diffrn_radiation_wavelength']['wavelength'] = dict(Parameter(
                                item.wavelength,
                                error = item.wavelength_sigma,
                                category = '_diffrn_radiation_wavelength',
                                prettyCategory = 'radiation',
                                name = 'wavelength',
                                prettyName = 'wavelength',
                                shortPrettyName = 'wavelength',
                                icon = 'radiation',
                                url = 'https://docs.easydiffraction.org/app/project/dictionaries/_diffrn_radiation/',
                                cifDict = 'core',
                                absDelta = 0.01,
                                units = 'Å',
                                fittable = True,
                                fit = item.wavelength_refinement
                            ))
                        if hasattr(item, 'offset_ttheta'):
                            if not '_pd_calib' in ed_experiment_no_meas['params']:
                                ed_experiment_no_meas['params']['_pd_calib'] = {}
                            ed_experiment_no_meas['params']['_pd_calib']['2theta_offset'] = dict(Parameter(
                                item.offset_ttheta,
                                error = item.offset_ttheta_sigma,
                                category = '_pd_calib',
                                prettyCategory = 'calib',
                                name = '2theta_offset',
                                prettyName = '2θ offset',
                                shortPrettyName = 'offset',
                                icon = 'arrows-alt-h',
                                url = 'https://docs.easydiffraction.org/app/project/dictionaries/_pd_calib/',
                                cifDict = 'pd',
                                absDelta = 0.2,
                                units = '°',
                                fittable = True,
                                fit = item.offset_ttheta_refinement
                            ))

                    # Cryspy instrument resolution section (CW)
                    elif type(item) is cryspy.C_item_loop_classes.cl_1_pd_instr_resolution.PdInstrResolution:
                        if hasattr(item, 'u') and hasattr(item, 'v') and hasattr(item, 'w') and hasattr(item, 'x') and hasattr(item, 'y'):
                            if not '_pd_instr' in ed_experiment_no_meas['params']:
                                ed_experiment_no_meas['params']['_pd_instr'] = {}
                            ed_experiment_no_meas['params']['_pd_instr']['resolution_u'] = dict(Parameter(
                                item.u,
                                error = item.u_sigma,
                                category = '_pd_instr',
                                prettyCategory = 'inst',
                                name = 'resolution_u',
                                prettyName = 'resolution u',
                                shortPrettyName = 'u',
                                icon = 'shapes',  # 'grip-lines-vertical'
                                url = 'https://docs.easydiffraction.org/app/project/dictionaries/_pd_instr/',
                                absDelta = 0.1,
                                fittable = True,
                                fit = item.u_refinement
                            ))
                            ed_experiment_no_meas['params']['_pd_instr']['resolution_v'] = dict(Parameter(
                                item.v,
                                error = item.v_sigma,
                                category = '_pd_instr',
                                prettyCategory = 'inst',
                                name = 'resolution_v',
                                prettyName = 'resolution v',
                                shortPrettyName = 'v',
                                icon = 'shapes',  # 'grip-lines-vertical'
                                url = 'https://docs.easydiffraction.org/app/project/dictionaries/_pd_instr/',
                                absDelta = 0.1,
                                fittable = True,
                                fit = item.v_refinement
                            ))
                            ed_experiment_no_meas['params']['_pd_instr']['resolution_w'] = dict(Parameter(
                                item.w,
                                error = item.w_sigma,
                                category = '_pd_instr',
                                prettyCategory = 'inst',
                                name = 'resolution_w',
                                prettyName = 'resolution w',
                                shortPrettyName = 'w',
                                icon = 'shapes',  # 'grip-lines-vertical'
                                url = 'https://docs.easydiffraction.org/app/project/dictionaries/_pd_instr/',
                                absDelta = 0.1,
                                fittable = True,
                                fit = item.w_refinement
                            ))
                            ed_experiment_no_meas['params']['_pd_instr']['resolution_x'] = dict(Parameter(
                                item.x,
                                error = item.x_sigma,
                                category = '_pd_instr',
                                prettyCategory = 'inst',
                                name = 'resolution_x',
                                prettyName = 'resolution x',
                                shortPrettyName = 'x',
                                icon = 'shapes',  # 'grip-lines-vertical'
                                url = 'https://docs.easydiffraction.org/app/project/dictionaries/_pd_instr/',
                                absDelta = 0.1,
                                fittable = True,
                                fit = item.x_refinement
                            ))
                            ed_experiment_no_meas['params']['_pd_instr']['resolution_y'] = dict(Parameter(
                                item.y,
                                error = item.y_sigma,
                                category = '_pd_instr',
                                prettyCategory = 'inst',
                                name = 'resolution_y',
                                prettyName = 'resolution y',
                                shortPrettyName = 'y',
                                icon = 'shapes',  # 'grip-lines-vertical'
                                url = 'https://docs.easydiffraction.org/app/project/dictionaries/_pd_instr/',
                                absDelta = 0.1,
                                fittable = True,
                                fit = item.y_refinement
                            ))

                    # Cryspy peak asymmetries section (CW)
                    elif type(item) is cryspy.C_item_loop_classes.cl_1_pd_instr_reflex_asymmetry.PdInstrReflexAsymmetry:
                        if hasattr(item, 'p1') and hasattr(item, 'p2') and hasattr(item, 'p3') and hasattr(item, 'p4'):
                            if not '_pd_instr' in ed_experiment_no_meas['params']:
                                ed_experiment_no_meas['params']['_pd_instr'] = {}
                            ed_experiment_no_meas['params']['_pd_instr']['reflex_asymmetry_p1'] = dict(Parameter(
                                item.p1,
                                error = item.p1_sigma,
                                category = '_pd_instr',
                                prettyCategory = 'inst',
                                name = 'reflex_asymmetry_p1',
                                prettyName = 'asymmetry p1',
                                shortPrettyName = 'p1',
                                icon = 'balance-scale-left',
                                url = 'https://docs.easydiffraction.org/app/project/dictionaries/_pd_instr/',
                                absDelta = 0.5,
                                fittable = True,
                                fit = item.p1_refinement
                            ))
                            ed_experiment_no_meas['params']['_pd_instr']['reflex_asymmetry_p2'] = dict(Parameter(
                                item.p2,
                                error = item.p2_sigma,
                                category = '_pd_instr',
                                prettyCategory = 'inst',
                                name = 'reflex_asymmetry_p2',
                                prettyName = 'asymmetry p2',
                                shortPrettyName = 'p2',
                                icon = 'balance-scale-left',
                                url = 'https://docs.easydiffraction.org/app/project/dictionaries/_pd_instr/',
                                absDelta = 0.5,
                                fittable = True,
                                fit = item.p2_refinement
                            ))
                            ed_experiment_no_meas['params']['_pd_instr']['reflex_asymmetry_p3'] = dict(Parameter(
                                item.p3,
                                error = item.p3_sigma,
                                category = '_pd_instr',
                                prettyCategory = 'inst',
                                name = 'reflex_asymmetry_p3',
                                prettyName = 'asymmetry p3',
                                shortPrettyName = 'p3',
                                icon = 'balance-scale-left',
                                url = 'https://docs.easydiffraction.org/app/project/dictionaries/_pd_instr/',
                                absDelta = 0.5,
                                fittable = True,
                                fit = item.p3_refinement
                            ))
                            ed_experiment_no_meas['params']['_pd_instr']['reflex_asymmetry_p4'] = dict(Parameter(
                                item.p4,
                                error = item.p4_sigma,
                                category = '_pd_instr',
                                prettyCategory = 'inst',
                                name = 'reflex_asymmetry_p4',
                                prettyName = 'asymmetry p4',
                                shortPrettyName = 'p4',
                                icon = 'balance-scale-left',
                                url = 'https://docs.easydiffraction.org/app/project/dictionaries/_pd_instr/',
                                absDelta = 0.5,
                                fittable = True,
                                fit = item.p4_refinement
                            ))

                    # Cryspy parameters section (TOF)
                    elif type(item) is cryspy.C_item_loop_classes.cl_1_tof_parameters.TOFParameters:
                        if hasattr(item, 'zero') and hasattr(item, 'dtt1') and hasattr(item, 'dtt2') and hasattr(item, 'ttheta_bank'):
                            if not '_pd_instr' in ed_experiment_no_meas['params']:
                                ed_experiment_no_meas['params']['_pd_instr'] = {}
                            ed_experiment_no_meas['params']['_pd_instr']['2theta_bank'] = dict(Parameter(
                                item.ttheta_bank,
                                category = '_pd_instr',
                                prettyCategory = 'inst',
                                name = '2theta_bank',
                                prettyName = '2theta bank',
                                shortPrettyName = '2θ bank',
                                icon = 'hashtag',
                                url = 'https://docs.easydiffraction.org/app/project/dictionaries/_pd_instr/',
                                fittable = False
                            ))
                            ed_experiment_no_meas['params']['_pd_instr']['dtt1'] = dict(Parameter(
                                item.dtt1,
                                error = item.dtt1_sigma,
                                category = '_pd_instr',
                                prettyCategory = 'inst',
                                name = 'dtt1',  # DIFC in GSAS
                                prettyName = 'dtt1',
                                shortPrettyName = 'dtt1',
                                icon = 'radiation',
                                url = 'https://docs.easydiffraction.org/app/project/dictionaries/_pd_instr/',
                                absDelta = 100.0,
                                fittable = True,
                                fit = item.dtt1_refinement
                            ))
                            ed_experiment_no_meas['params']['_pd_instr']['dtt2'] = dict(Parameter(
                                item.dtt2,
                                error = item.dtt2_sigma,
                                category = '_pd_instr',
                                prettyCategory = 'inst',
                                name = 'dtt2',  # DIFA in GSAS
                                prettyName = 'dtt2',
                                shortPrettyName = 'dtt2',
                                icon = 'radiation',
                                url = 'https://docs.easydiffraction.org/app/project/dictionaries/_pd_instr/',
                                absDelta = 0.1,
                                fittable = True,
                                fit = item.dtt2_refinement
                            ))
                            ed_experiment_no_meas['params']['_pd_instr']['zero'] = dict(Parameter(
                                item.zero,
                                error = item.zero_sigma,
                                category = '_pd_instr',
                                prettyCategory = 'inst',
                                name = 'zero',  # TZERO in GSAS
                                prettyName = 'zero',
                                shortPrettyName = 'zero',
                                icon = 'arrows-alt-h',
                                url = 'https://docs.easydiffraction.org/app/project/dictionaries/_pd_instr/',
                                absDelta = 0.5,
                                fittable = True,
                                fit = item.zero_refinement
                            ))

                    # Cryspy peak profile section (TOF)
                    elif type(item) is cryspy.C_item_loop_classes.cl_1_tof_profile.TOFProfile:
                        if hasattr(item, 'alpha0') and hasattr(item, 'beta0') and hasattr(item, 'sigma0'):
                            if not '_pd_instr' in ed_experiment_no_meas['params']:
                                ed_experiment_no_meas['params']['_pd_instr'] = {}
                            ed_experiment_no_meas['params']['_pd_instr']['alpha0'] = dict(Parameter(
                                item.alpha0,
                                error = item.alpha0_sigma,
                                category = '_pd_instr',
                                prettyCategory = 'inst',
                                name = 'alpha0',
                                prettyName = 'alpha0',
                                shortPrettyName = 'α0',
                                icon = 'shapes',
                                url = 'https://docs.easydiffraction.org/app/project/dictionaries/_pd_instr/',
                                absDelta = 0.5,
                                fittable = True,
                                fit = item.alpha0_refinement
                            ))
                            ed_experiment_no_meas['params']['_pd_instr']['alpha1'] = dict(Parameter(
                                item.alpha1,
                                error = item.alpha1_sigma,
                                category = '_pd_instr',
                                prettyCategory = 'inst',
                                name = 'alpha1',
                                prettyName = 'alpha1',
                                shortPrettyName = 'α1',
                                icon = 'shapes',
                                url = 'https://docs.easydiffraction.org/app/project/dictionaries/_pd_instr/',
                                absDelta = 0.5,
                                fittable = True,
                                fit = item.alpha1_refinement
                            ))
                            ed_experiment_no_meas['params']['_pd_instr']['beta0'] = dict(Parameter(
                                item.beta0,
                                error = item.beta0_sigma,
                                category = '_pd_instr',
                                prettyCategory = 'inst',
                                name = 'beta0',
                                prettyName = 'beta0',
                                shortPrettyName = 'β0',
                                icon = 'shapes',
                                url = 'https://docs.easydiffraction.org/app/project/dictionaries/_pd_instr/',
                                absDelta = 0.5,
                                fittable = True,
                                fit = item.beta0_refinement
                            ))
                            ed_experiment_no_meas['params']['_pd_instr']['beta1'] = dict(Parameter(
                                item.beta1,
                                error = item.beta1_sigma,
                                category = '_pd_instr',
                                prettyCategory = 'inst',
                                name = 'beta1',
                                prettyName = 'beta1',
                                shortPrettyName = 'β1',
                                icon = 'shapes',
                                url = 'https://docs.easydiffraction.org/app/project/dictionaries/_pd_instr/',
                                absDelta = 0.5,
                                fittable = True,
                                fit = item.beta1_refinement
                            ))
                            ed_experiment_no_meas['params']['_pd_instr']['sigma0'] = dict(Parameter(
                                item.sigma0,
                                error = item.sigma0_sigma,
                                category = '_pd_instr',
                                prettyCategory = 'inst',
                                name = 'sigma0',
                                prettyName = 'sigma0',
                                shortPrettyName = 'σ0',
                                icon = 'shapes',
                                url = 'https://docs.easydiffraction.org/app/project/dictionaries/_pd_instr/',
                                absDelta = 0.5,
                                fittable = True,
                                fit = item.sigma0_refinement
                            ))
                            ed_experiment_no_meas['params']['_pd_instr']['sigma1'] = dict(Parameter(
                                item.sigma1,
                                error = item.sigma1_sigma,
                                category = '_pd_instr',
                                prettyCategory = 'inst',
                                name = 'sigma1',
                                prettyName = 'sigma1',
                                shortPrettyName = 'σ1',
                                icon = 'shapes',
                                url = 'https://docs.easydiffraction.org/app/project/dictionaries/_pd_instr/',
                                absDelta = 0.5,
                                fittable = True,
                                fit = item.sigma1_refinement
                            ))
                            ed_experiment_no_meas['params']['_pd_instr']['sigma2'] = dict(Parameter(
                                item.sigma2,
                                error = item.sigma2_sigma,
                                category = '_pd_instr',
                                prettyCategory = 'inst',
                                name = 'sigma2',
                                prettyName = 'sigma2',
                                shortPrettyName = 'σ2',
                                icon = 'shapes',
                                url = 'https://docs.easydiffraction.org/app/project/dictionaries/_pd_instr/',
                                absDelta = 0.5,
                                fittable = True,
                                fit = item.sigma2_refinement
                            ))
                            #ed_experiment_no_meas['params']['_pd_instr']['gamma0'] = dict(Parameter(
                            #    item.gamma0,
                            #    error = item.gamma0_sigma,
                            #    category = '_pd_instr',
                            #    prettyCategory = 'inst',
                            #    name = 'gamma0',
                            #    prettyName = 'gamma0',
                            #    shortPrettyName = 'γ0',
                            #    icon = 'shapes',
                            #    url = 'https://docs.easydiffraction.org/app/project/dictionaries/_pd_instr/',
                            #    absDelta = 0.5,
                            #    fittable = True,
                            #    fit = item.gamma0_refinement
                            #))
                            #ed_experiment_no_meas['params']['_pd_instr']['gamma1'] = dict(Parameter(
                            #    item.gamma1,
                            #    error = item.gamma1_sigma,
                            #    category = '_pd_instr',
                            #    prettyCategory = 'inst',
                            #    name = 'gamma1',
                            #    prettyName = 'gamma1',
                            #    shortPrettyName = 'γ1',
                            #    icon = 'shapes',
                            #    url = 'https://docs.easydiffraction.org/app/project/dictionaries/_pd_instr/',
                            #    absDelta = 0.5,
                            #    fittable = True,
                            #    fit = item.gamma1_refinement
                            #))
                            #ed_experiment_no_meas['params']['_pd_instr']['gamma2'] = dict(Parameter(
                            #    item.gamma2,
                            #    error = item.gamma2_sigma,
                            #    category = '_pd_instr',
                            #    prettyCategory = 'inst',
                            #    name = 'gamma2',
                            #    prettyName = 'gamma2',
                            #    shortPrettyName = 'γ2',
                            #    icon = 'shapes',
                            #    url = 'https://docs.easydiffraction.org/app/project/dictionaries/_pd_instr/',
                            #    absDelta = 0.5,
                            #    fittable = True,
                            #    fit = item.gamma2_refinement
                            #))

                    # Ed (pycifstar processed) background section
                    elif type(item) is cryspy.B_parent_classes.cl_2_loop.LoopN and item.items[0].PREFIX == 'pd_background':
                        pycifstar_bkg_points = item.items
                        ed_bkg_points = []
                        for idx, pycifstar_bkg_point in enumerate(pycifstar_bkg_points):
                            ed_bkg_point = {}
                            ed_bkg_point['line_segment_X'] = dict(Parameter(
                                pycifstar_bkg_point.line_segment_x,
                                idx = idx,
                                category = '_pd_background',
                                name = 'line_segment_X',
                                prettyName = 'TOF',
                                shortPrettyName = 'TOF',
                                url = 'https://docs.easydiffraction.org/app/project/dictionaries/_pd_background/',
                                cifDict = 'pd'
                            ))
                            ed_bkg_point['line_segment_intensity'] = dict(Parameter(
                                pycifstar_bkg_point.line_segment_intensity,
                                #error = pycifstar_bkg_point.line_segment_intensity_sigma,
                                error = 1.0,
                                idx = idx,
                                category = '_pd_background',
                                prettyCategory = 'bkg',
                                rowName = f'{pycifstar_bkg_point.line_segment_x:g}µs',  # formatting float to str without trailing zeros
                                name = 'line_segment_intensity',
                                prettyName = 'intensity',
                                shortPrettyName = 'Ibkg',
                                icon = 'mountain',
                                categoryIcon = 'wave-square',
                                url = 'https://docs.easydiffraction.org/app/project/dictionaries/_pd_background/',
                                cifDict = 'pd',
                                pctDelta = 25,
                                fittable = True,
                                fit = pycifstar_bkg_point.line_segment_intensity_refinement
                            ))
                            ed_bkg_point['X_coordinate'] = dict(Parameter(
                                'time-of-flight',
                                idx = idx,
                                category = '_pd_background',
                                name = 'X_coordinate',
                                prettyName = 'X coord',
                                shortPrettyName = 'X coord',
                                url = 'https://docs.easydiffraction.org/app/project/dictionaries/_pd_background/',
                                cifDict = 'pd'
                            ))
                            ed_bkg_points.append(ed_bkg_point)
                        ed_experiment_no_meas['loops']['_pd_background'] = ed_bkg_points

                    # Cryspy background section (TOF, polinom coeffs?)
                    elif type(item) is cryspy.C_item_loop_classes.cl_1_tof_background.TOFBackground:
                        if hasattr(item, 'time_max'):
                            if not '_tof_background' in ed_experiment_no_meas['params']:
                                ed_experiment_no_meas['params']['_tof_background'] = {}
                            ed_experiment_no_meas['params']['_tof_background']['time_max'] = dict(Parameter(
                                item.time_max,
                                optional=True,
                                category = '_tof_background',
                                prettyCategory = 'bkg',
                                name = 'time_max',  # Is this the name used on save cif?
                                prettyName = 'TOF max',
                                shortPrettyName = 'max',
                                url = 'https://docs.easydiffraction.org/app/project/dictionaries/_pd_instr/',
                            ))
                            ed_experiment_no_meas['params']['_tof_background']['coeff1'] = dict(Parameter(
                                item.coeff1 if hasattr(item, 'coeff1') else 0.0,
                                error = item.coeff1_sigma,
                                category = '_tof_background',
                                prettyCategory = 'bkg',
                                name = 'coeff1',
                                prettyName = 'coeff1',
                                shortPrettyName = 'c1',
                                categoryIcon = 'wave-square',
                                url = 'https://docs.easydiffraction.org/app/project/dictionaries/_pd_background/',
                                pctDelta = 25,
                                fittable = True,
                                fit = item.coeff1_refinement
                            ))
                            ed_experiment_no_meas['params']['_tof_background']['coeff2'] = dict(Parameter(
                                item.coeff2 if hasattr(item, 'coeff2') else 0.0,
                                error = item.coeff2_sigma,
                                category = '_tof_background',
                                prettyCategory = 'bkg',
                                name = 'coeff2',
                                prettyName = 'coeff2',
                                shortPrettyName = 'c2',
                                categoryIcon = 'wave-square',
                                url = 'https://docs.easydiffraction.org/app/project/dictionaries/_pd_background/',
                                pctDelta = 25,
                                fittable = True,
                                fit = item.coeff2_refinement
                            ))
                            ed_experiment_no_meas['params']['_tof_background']['coeff3'] = dict(Parameter(
                                item.coeff3 if hasattr(item, 'coeff3') else 0.0,
                                error = item.coeff3_sigma,
                                category = '_tof_background',
                                prettyCategory = 'bkg',
                                name = 'coeff3',
                                prettyName = 'coeff3',
                                shortPrettyName = 'c3',
                                categoryIcon = 'wave-square',
                                url = 'https://docs.easydiffraction.org/app/project/dictionaries/_pd_background/',
                                pctDelta = 25,
                                fittable = True,
                                fit = item.coeff3_refinement
                            ))
                            ed_experiment_no_meas['params']['_tof_background']['coeff4'] = dict(Parameter(
                                item.coeff4 if hasattr(item, 'coeff4') else 0.0,
                                error = item.coeff4_sigma,
                                category = '_tof_background',
                                prettyCategory = 'bkg',
                                name = 'coeff4',
                                prettyName = 'coeff4',
                                shortPrettyName = 'c4',
                                categoryIcon = 'wave-square',
                                url = 'https://docs.easydiffraction.org/app/project/dictionaries/_pd_background/',
                                pctDelta = 25,
                                fittable = True,
                                fit = item.coeff4_refinement
                            ))
                            ed_experiment_no_meas['params']['_tof_background']['coeff5'] = dict(Parameter(
                                item.coeff5 if hasattr(item, 'coeff5') else 0.0,
                                error = item.coeff5_sigma,
                                category = '_tof_background',
                                prettyCategory = 'bkg',
                                name = 'coeff5',
                                prettyName = 'coeff5',
                                shortPrettyName = 'c5',
                                categoryIcon = 'wave-square',
                                url = 'https://docs.easydiffraction.org/app/project/dictionaries/_pd_background/',
                                pctDelta = 25,
                                fittable = True,
                                fit = item.coeff5_refinement
                            ))
                            ed_experiment_no_meas['params']['_tof_background']['coeff6'] = dict(Parameter(
                                item.coeff6 if hasattr(item, 'coeff6') else 0.0,
                                error = item.coeff6_sigma,
                                category = '_tof_background',
                                prettyCategory = 'bkg',
                                name = 'coeff6',
                                prettyName = 'coeff6',
                                shortPrettyName = 'c6',
                                categoryIcon = 'wave-square',
                                url = 'https://docs.easydiffraction.org/app/project/dictionaries/_pd_background/',
                                pctDelta = 25,
                                fittable = True,
                                fit = item.coeff6_refinement
                            ))
                            ed_experiment_no_meas['params']['_tof_background']['coeff7'] = dict(Parameter(
                                item.coeff7 if hasattr(item, 'coeff7') else 0.0,
                                error = item.coeff7_sigma,
                                category = '_tof_background',
                                prettyCategory = 'bkg',
                                name = 'coeff7',
                                prettyName = 'coeff7',
                                shortPrettyName = 'c7',
                                categoryIcon = 'wave-square',
                                url = 'https://docs.easydiffraction.org/app/project/dictionaries/_pd_background/',
                                pctDelta = 25,
                                fittable = True,
                                fit = item.coeff7_refinement
                            ))
                            ed_experiment_no_meas['params']['_tof_background']['coeff8'] = dict(Parameter(
                                item.coeff8 if hasattr(item, 'coeff8') else 0.0,
                                error = item.coeff8_sigma,
                                category = '_tof_background',
                                prettyCategory = 'bkg',
                                name = 'coeff8',
                                prettyName = 'coeff8',
                                shortPrettyName = 'c8',
                                categoryIcon = 'wave-square',
                                url = 'https://docs.easydiffraction.org/app/project/dictionaries/_pd_background/',
                                pctDelta = 25,
                                fittable = True,
                                fit = item.coeff8_refinement
                            ))
                            ed_experiment_no_meas['params']['_tof_background']['coeff9'] = dict(Parameter(
                                item.coeff9 if hasattr(item, 'coeff9') else 0.0,
                                error = item.coeff9_sigma,
                                category = '_tof_background',
                                prettyCategory = 'bkg',
                                name = 'coeff9',
                                prettyName = 'coeff9',
                                shortPrettyName = 'c9',
                                categoryIcon = 'wave-square',
                                url = 'https://docs.easydiffraction.org/app/project/dictionaries/_pd_background/',
                                pctDelta = 25,
                                fittable = True,
                                fit = item.coeff9_refinement
                            ))
                            ed_experiment_no_meas['params']['_tof_background']['coeff10'] = dict(Parameter(
                                item.coeff10 if hasattr(item, 'coeff10') else 0.0,
                                error = item.coeff10_sigma,
                                category = '_tof_background',
                                prettyCategory = 'bkg',
                                name = 'coeff10',
                                prettyName = 'coeff10',
                                shortPrettyName = 'c10',
                                categoryIcon = 'wave-square',
                                url = 'https://docs.easydiffraction.org/app/project/dictionaries/_pd_background/',
                                pctDelta = 25,
                                fittable = True,
                                fit = item.coeff10_refinement
                            ))
                            ed_experiment_no_meas['params']['_tof_background']['coeff11'] = dict(Parameter(
                                item.coeff11 if hasattr(item, 'coeff11') else 0.0,
                                error = item.coeff11_sigma,
                                category = '_tof_background',
                                prettyCategory = 'bkg',
                                name = 'coeff11',
                                prettyName = 'coeff11',
                                shortPrettyName = 'c11',
                                categoryIcon = 'wave-square',
                                url = 'https://docs.easydiffraction.org/app/project/dictionaries/_pd_background/',
                                pctDelta = 25,
                                fittable = True,
                                fit = item.coeff11_refinement
                            ))
                            ed_experiment_no_meas['params']['_tof_background']['coeff12'] = dict(Parameter(
                                item.coeff12 if hasattr(item, 'coeff12') else 0.0,
                                error = item.coeff12_sigma,
                                category = '_tof_background',
                                prettyCategory = 'bkg',
                                name = 'coeff12',
                                prettyName = 'coeff12',
                                shortPrettyName = 'c12',
                                categoryIcon = 'wave-square',
                                url = 'https://docs.easydiffraction.org/app/project/dictionaries/_pd_background/',
                                pctDelta = 25,
                                fittable = True,
                                fit = item.coeff12_refinement
                            ))
                            ed_experiment_no_meas['params']['_tof_background']['coeff13'] = dict(Parameter(
                                item.coeff13 if hasattr(item, 'coeff13') else 0.0,
                                error = item.coeff13_sigma,
                                category = '_tof_background',
                                prettyCategory = 'bkg',
                                name = 'coeff13',
                                prettyName = 'coeff13',
                                shortPrettyName = 'c13',
                                categoryIcon = 'wave-square',
                                url = 'https://docs.easydiffraction.org/app/project/dictionaries/_pd_background/',
                                pctDelta = 25,
                                fittable = True,
                                fit = item.coeff13_refinement
                            ))
                            ed_experiment_no_meas['params']['_tof_background']['coeff14'] = dict(Parameter(
                                item.coeff14 if hasattr(item, 'coeff14') else 0.0,
                                error = item.coeff14_sigma,
                                category = '_tof_background',
                                prettyCategory = 'bkg',
                                name = 'coeff14',
                                prettyName = 'coeff14',
                                shortPrettyName = 'c14',
                                categoryIcon = 'wave-square',
                                url = 'https://docs.easydiffraction.org/app/project/dictionaries/_pd_background/',
                                pctDelta = 25,
                                fittable = True,
                                fit = item.coeff14_refinement
                            ))
                            ed_experiment_no_meas['params']['_tof_background']['coeff15'] = dict(Parameter(
                                item.coeff15 if hasattr(item, 'coeff15') else 0.0,
                                error = item.coeff15_sigma,
                                category = '_tof_background',
                                prettyCategory = 'bkg',
                                name = 'coeff15',
                                prettyName = 'coeff15',
                                shortPrettyName = 'c15',
                                categoryIcon = 'wave-square',
                                url = 'https://docs.easydiffraction.org/app/project/dictionaries/_pd_background/',
                                pctDelta = 25,
                                fittable = True,
                                fit = item.coeff15_refinement
                            ))
                            ed_experiment_no_meas['params']['_tof_background']['coeff16'] = dict(Parameter(
                                item.coeff16 if hasattr(item, 'coeff16') else 0.0,
                                error = item.coeff16_sigma,
                                category = '_tof_background',
                                prettyCategory = 'bkg',
                                name = 'coeff16',
                                prettyName = 'coeff16',
                                shortPrettyName = 'c16',
                                categoryIcon = 'wave-square',
                                url = 'https://docs.easydiffraction.org/app/project/dictionaries/_pd_background/',
                                pctDelta = 25,
                                fittable = True,
                                fit = item.coeff16_refinement
                            ))
                            ed_experiment_no_meas['params']['_tof_background']['coeff17'] = dict(Parameter(
                                item.coeff17 if hasattr(item, 'coeff17') else 0.0,
                                error = item.coeff17_sigma,
                                category = '_tof_background',
                                prettyCategory = 'bkg',
                                name = 'coeff17',
                                prettyName = 'coeff17',
                                shortPrettyName = 'c17',
                                categoryIcon = 'wave-square',
                                url = 'https://docs.easydiffraction.org/app/project/dictionaries/_pd_background/',
                                pctDelta = 25,
                                fittable = True,
                                fit = item.coeff17_refinement
                            ))
                            ed_experiment_no_meas['params']['_tof_background']['coeff18'] = dict(Parameter(
                                item.coeff18 if hasattr(item, 'coeff18') else 0.0,
                                error = item.coeff18_sigma,
                                category = '_tof_background',
                                prettyCategory = 'bkg',
                                name = 'coeff18',
                                prettyName = 'coeff18',
                                shortPrettyName = 'c18',
                                categoryIcon = 'wave-square',
                                url = 'https://docs.easydiffraction.org/app/project/dictionaries/_pd_background/',
                                pctDelta = 25,
                                fittable = True,
                                fit = item.coeff18_refinement
                            ))

                    # Cryspy background section (CW, points)
                    elif type(item) is cryspy.C_item_loop_classes.cl_1_pd_background.PdBackgroundL:
                        cryspy_bkg_points = item.items
                        ed_bkg_points = []
                        for idx, cryspy_bkg_point in enumerate(cryspy_bkg_points):
                            ed_bkg_point = {}
                            ed_bkg_point['line_segment_X'] = dict(Parameter(
                                cryspy_bkg_point.ttheta,
                                idx = idx,
                                category = '_pd_background',
                                name = 'line_segment_X',
                                prettyName = '2θ',
                                shortPrettyName = '2θ',
                                url = 'https://docs.easydiffraction.org/app/project/dictionaries/_pd_background/',
                                cifDict = 'pd'
                            ))
                            ed_bkg_point['line_segment_intensity'] = dict(Parameter(
                                cryspy_bkg_point.intensity,
                                error = cryspy_bkg_point.intensity_sigma,
                                idx = idx,
                                category = '_pd_background',
                                prettyCategory = 'bkg',
                                rowName = f'{cryspy_bkg_point.ttheta:g}°',  # formatting float to str without trailing zeros
                                name = 'line_segment_intensity',
                                prettyName = 'intensity',
                                shortPrettyName = 'Ibkg',
                                icon = 'mountain',
                                categoryIcon = 'wave-square',
                                url = 'https://docs.easydiffraction.org/app/project/dictionaries/_pd_background/',
                                cifDict = 'pd',
                                pctDelta = 25,
                                fittable = True,
                                fit = cryspy_bkg_point.intensity_refinement
                            ))
                            ed_bkg_point['X_coordinate'] = dict(Parameter(
                                '2theta',
                                idx = idx,
                                category = '_pd_background',
                                name = 'X_coordinate',
                                prettyName = 'X coord',
                                shortPrettyName = 'X coord',
                                url = 'https://docs.easydiffraction.org/app/project/dictionaries/_pd_background/',
                                cifDict = 'pd'
                            ))
                            ed_bkg_points.append(ed_bkg_point)
                        ed_experiment_no_meas['loops']['_pd_background'] = ed_bkg_points

                    # Cryspy measured data section (TOF)
                    elif type(item) is cryspy.C_item_loop_classes.cl_1_tof_meas.TOFMeasL:
                        if not '_diffrn_radiation' in ed_experiment_no_meas['params']:
                            ed_experiment_no_meas['params']['_diffrn_radiation'] = {}
                        ed_experiment_no_meas['params']['_diffrn_radiation']['type'] = dict(Parameter(
                            'tof',
                            optional=True,
                            category='_diffrn_radiation',
                            name='type',
                            shortPrettyName='type',
                            url='https://docs.easydiffraction.org/app/project/dictionaries/_diffrn_radiation/'
                        ))
                        cryspy_meas_points = item.items
                        ed_meas_points = []
                        for idx, cryspy_meas_point in enumerate(cryspy_meas_points):
                            ed_meas_point = {}
                            ed_meas_point['time_of_flight'] = dict(Parameter(
                                cryspy_meas_point.time,
                                idx = idx,
                                category = '_pd_meas',
                                name = 'time_of_flight',
                                shortPrettyName = 'tof',
                                url = 'https://docs.easydiffraction.org/app/project/dictionaries/_pd_meas/',
                                cifDict = 'pd'
                            ))
                            ed_meas_point['intensity_total'] = dict(Parameter(
                                cryspy_meas_point.intensity,
                                idx = idx,
                                category = '_pd_meas',
                                name = 'intensity_total',
                                shortPrettyName = 'I',
                                url = 'https://docs.easydiffraction.org/app/project/dictionaries/_pd_meas/',
                                cifDict = 'pd'
                            ))
                            ed_meas_point['intensity_total_su'] = dict(Parameter(
                                cryspy_meas_point.intensity_sigma,
                                idx = idx,
                                category = '_pd_meas',
                                name = 'intensity_total_su',
                                shortPrettyName = 'sI',
                                url = 'https://docs.easydiffraction.org/app/project/dictionaries/_pd_meas/',
                                cifDict = 'pd'
                            ))
                            ed_meas_points.append(ed_meas_point)
                        ed_experiment_meas_only['loops']['_pd_meas'] = ed_meas_points

                        # Modify range_inc based on the measured data points in _pd_meas loop
                        pd_meas_range_min = ed_meas_points[0]['time_of_flight']['value']
                        pd_meas_range_max = ed_meas_points[-1]['time_of_flight']['value']
                        pd_meas_range_inc = (pd_meas_range_max - pd_meas_range_min) / (len(ed_meas_points) - 1)
                        ed_experiment_no_meas['params']['_pd_meas']['tof_range_inc']['value'] = pd_meas_range_inc

                    # Cryspy measured data section (CW)
                    elif type(item) is cryspy.C_item_loop_classes.cl_1_pd_meas.PdMeasL:
                        if not '_diffrn_radiation' in ed_experiment_no_meas['params']:
                            ed_experiment_no_meas['params']['_diffrn_radiation'] = {}
                        ed_experiment_no_meas['params']['_diffrn_radiation']['type'] = dict(Parameter(
                            'cw',
                            optional=True,
                            category='_diffrn_radiation',
                            name='type',
                            shortPrettyName='type',
                            url='https://docs.easydiffraction.org/app/project/dictionaries/_diffrn_radiation/'
                        ))
                        cryspy_meas_points = item.items
                        ed_meas_points = []
                        for idx, cryspy_meas_point in enumerate(cryspy_meas_points):
                            ed_meas_point = {}
                            ed_meas_point['2theta_scan'] = dict(Parameter(
                                cryspy_meas_point.ttheta,
                                idx = idx,
                                category = '_pd_meas',
                                name = '2theta_scan',
                                shortPrettyName = '2θ',
                                url = 'https://docs.easydiffraction.org/app/project/dictionaries/_pd_meas/',
                                cifDict = 'pd'
                            ))
                            ed_meas_point['intensity_total'] = dict(Parameter(
                                cryspy_meas_point.intensity,
                                idx = idx,
                                category = '_pd_meas',
                                name = 'intensity_total',
                                shortPrettyName = 'I',
                                url = 'https://docs.easydiffraction.org/app/project/dictionaries/_pd_meas/',
                                cifDict = 'pd'
                            ))
                            ed_meas_point['intensity_total_su'] = dict(Parameter(
                                cryspy_meas_point.intensity_sigma,
                                idx = idx,
                                category = '_pd_meas',
                                name = 'intensity_total_su',
                                shortPrettyName = 'sI',
                                url = 'https://docs.easydiffraction.org/app/project/dictionaries/_pd_meas/',
                                cifDict = 'pd'
                            ))
                            ed_meas_points.append(ed_meas_point)
                        ed_experiment_meas_only['loops']['_pd_meas'] = ed_meas_points

                        # Modify range_inc based on the measured data points in _pd_meas loop
                        pd_meas_range_min = ed_meas_points[0]['2theta_scan']['value']
                        pd_meas_range_max = ed_meas_points[-1]['2theta_scan']['value']
                        pd_meas_range_inc = (pd_meas_range_max - pd_meas_range_min) / (len(ed_meas_points) - 1)
                        ed_experiment_no_meas['params']['_pd_meas']['2theta_range_inc']['value'] = pd_meas_range_inc

            if ed_experiment_meas_only is not None:
                ed_experiments_meas_only.append(ed_experiment_meas_only)
            if ed_experiment_no_meas is not None:
                ed_experiments_no_meas.append(ed_experiment_no_meas)

        return ed_experiments_meas_only, ed_experiments_no_meas
