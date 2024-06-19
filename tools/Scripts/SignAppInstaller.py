# SPDX-FileCopyrightText: 2021 easyDiffraction contributors <support@easydiffraction.org>
# SPDX-License-Identifier: BSD-3-Clause
# © 2021 Contributors to the easyDiffraction project <https://github.com/easyScience/easyDiffractionApp>

__author__ = "github.com/AndrewSazonov"
__version__ = '0.0.1'

import os
import sys
import time
import base64
import Config
import Functions


GIT_BRANCH = sys.argv[1]
MATRIX_OS = sys.argv[2]
MACOS_CERTIFICATE_ENCODED = sys.argv[3]       # Encoded content of the .p12 certificate file (exported from certificate of Developer ID Application type)
MACOS_CERTIFICATE_PASSWORD = sys.argv[4]      # Password associated with the .p12 certificate
APPSTORE_NOTARIZATION_USERNAME = sys.argv[5]  # Apple ID (esss.se personal account) added to https://developer.apple.com
APPSTORE_NOTARIZATION_PASSWORD = sys.argv[6]  # App specific password for EasyDiffraction from https://appleid.apple.com

CONFIG = Config.Config(GIT_BRANCH, MATRIX_OS)

IDENTITY = CONFIG['ci']['codesign']['apple']['identity']
BUNDLE_ID = CONFIG['ci']['codesign']['bundle_id']
TEAM_ID = CONFIG['ci']['codesign']['apple']['team_id']

print('IDENTITY', IDENTITY)
print('BUNDLE_ID', BUNDLE_ID)
print('TEAM_ID', TEAM_ID)


def debuggg():
    keychain_name = 'codesign.keychain'
    print('keychain_name', keychain_name)

    try:
        sub_message = f'sign installer app "{CONFIG.setup_exe_path}" with imported certificate'
        Functions.run(
            'codesign',
            '--deep',
            '--force',                      # replace any existing signature on the path(s) given
            '--verbose',                    # set (with a numeric value) or increments the verbosity level of output
            '--timestamp',                  # request that a default Apple timestamp authority server be contacted to authenticate the time of signin
            '--options=runtime',            # specify a set of option flags to be embedded in the code signature
            #'--keychain', keychain_name,    # specify keychain name
            #'--identifier', BUNDLE_ID,      # specify bundle id
            '--sign', TEAM_ID,              # sign the code at the path(s) given using this identity
            CONFIG.setup_exe_path)
    except Exception as sub_exception:
        Functions.printFailMessage(sub_message, sub_exception)
        sys.exit(1)
    else:
        Functions.printSuccessMessage(sub_message)

    exit()





def signLinux():
    Functions.printNeutralMessage('Code signing on Linux is not supported yet')
    return

def signWindows():
    Functions.printNeutralMessage('Code signing on Windows is not supported yet')
    return

def signMacos():
    try:
        ##########################
        # Prepare for code signing
        ##########################

        message = f'sign code on {CONFIG.os}'
        keychain_name = 'codesign.keychain'
        keychain_password = 'password'
        mac_certificate_fname = 'certificate.p12'

        try:
            sub_message = f'create keychain "{keychain_name}"'
            Functions.run(
                'security', 'create-keychain',
                '-p', keychain_password,
                keychain_name)
        except Exception as sub_exception:
            Functions.printFailMessage(sub_message, sub_exception)
            sys.exit(1)
        else:
            Functions.printSuccessMessage(sub_message)

        try:
            sub_message = f'set created keychain "{keychain_name}" to be default keychain'
            Functions.run(
                'security', 'default-keychain',
                '-s', keychain_name)
        except Exception as sub_exception:
            Functions.printFailMessage(sub_message, sub_exception)
            sys.exit(1)
        else:
            Functions.printSuccessMessage(sub_message)

        try:
            sub_message = f'list keychains'
            Functions.run(
                'security', 'list-keychains')
        except Exception as sub_exception:
            Functions.printFailMessage(sub_message, sub_exception)
            sys.exit(1)
        else:
            Functions.printSuccessMessage(sub_message)

        try:
            sub_message = f'unlock created keychain "{keychain_name}"'
            Functions.run(
                'security', 'unlock-keychain',
                '-p', keychain_password,
                keychain_name)
        except Exception as sub_exception:
            Functions.printFailMessage(sub_message, sub_exception)
            sys.exit(1)
        else:
            Functions.printSuccessMessage(sub_message)

        try:
            sub_message = f'create certificate file "{mac_certificate_fname}"'
            certificate_decoded = base64.b64decode(MACOS_CERTIFICATE_ENCODED)
            with open(mac_certificate_fname, 'wb') as f:
                f.write(certificate_decoded)
        except Exception as sub_exception:
            Functions.printFailMessage(sub_message, sub_exception)
            sys.exit(1)
        else:
            Functions.printSuccessMessage(sub_message)

        try:
            sub_message = f'import certificate "{mac_certificate_fname}" to created keychain "{keychain_name}"'
            Functions.run(
                'security', 'import',
                mac_certificate_fname,
                '-k', keychain_name,
                '-P', MACOS_CERTIFICATE_PASSWORD)
        except Exception as sub_exception:
            Functions.printFailMessage(sub_message, sub_exception)
            sys.exit(1)
        else:
            Functions.printSuccessMessage(sub_message)

        try:
            sub_message = f'show certificates'
            Functions.run(
                'security', 'find-identity',
                keychain_name)
        except Exception as sub_exception:
            Functions.printFailMessage(sub_message, sub_exception)
            sys.exit(1)
        else:
            Functions.printSuccessMessage(sub_message)

        try:
            sub_message = f'allow codesign to access certificate key from keychain "{keychain_name}"'
            Functions.run(
                'security', 'set-key-partition-list',
                '-S', 'apple-tool:,apple:,codesign:',
                '-s',
                '-k', keychain_password, keychain_name)
        except Exception as sub_exception:
            Functions.printFailMessage(sub_message, sub_exception)
            sys.exit(1)
        else:
            Functions.printSuccessMessage(sub_message)

        ####################
        # Sign app installer
        ####################

        try:
            sub_message = f'display information about the code at "{CONFIG.setup_exe_path}" before signing'
            Functions.run(
                'codesign',
                '--display',
                '--verbose',
                CONFIG.setup_exe_path)
        except Exception as sub_exception:
            Functions.printFailMessage(sub_message, sub_exception)
            sys.exit(1)
        else:
            Functions.printSuccessMessage(sub_message)

        try:
            sub_message = f'verify app signatures for installer "{CONFIG.setup_exe_path}" before signing'
            Functions.run(
                'codesign',
                '--verify',                 # verification of code signatures
                '--verbose',                # set (with a numeric value) or increments the verbosity level of output
                CONFIG.setup_exe_path)
        except Exception as sub_exception:
            Functions.printFailMessage(sub_message, sub_exception)
            sys.exit(1)
        else:
            Functions.printSuccessMessage(sub_message)

        try:
            sub_message = f'sign installer app "{CONFIG.setup_exe_path}" with imported certificate'
            Functions.run(
                'codesign',
                '--force',                      # replace any existing signature on the path(s) given
                '--verbose',                    # set (with a numeric value) or increments the verbosity level of output
                '--timestamp',                  # request that a default Apple timestamp authority server be contacted to authenticate the time of signin
                '--options=runtime',            # specify a set of option flags to be embedded in the code signature
                #'--keychain', keychain_name,    # specify keychain name
                #'--identifier', BUNDLE_ID,      # specify bundle id
                '--sign', TEAM_ID,              # sign the code at the path(s) given using this identity
                CONFIG.setup_exe_path)
        except Exception as sub_exception:
            Functions.printFailMessage(sub_message, sub_exception)
            sys.exit(1)
        else:
            Functions.printSuccessMessage(sub_message)

        return

        try:
            sub_message = f'display information about the code at "{CONFIG.setup_exe_path}" after signing'
            Functions.run(
                'codesign',
                '--display',
                '--verbose',
                CONFIG.setup_exe_path)
        except Exception as sub_exception:
            Functions.printFailMessage(sub_message, sub_exception)
            sys.exit(1)
        else:
            Functions.printSuccessMessage(sub_message)

        try:
            sub_message = f'verify app signatures for installer "{CONFIG.setup_exe_path}" after signing'
            Functions.run(
                'codesign',
                '--verify',                 # verification of code signatures
                '--verbose',                # set (with a numeric value) or increments the verbosity level of output
                CONFIG.setup_exe_path)
        except Exception as sub_exception:
            Functions.printFailMessage(sub_message, sub_exception)
            sys.exit(1)
        else:
            Functions.printSuccessMessage(sub_message)

        ########################
        # Notarize app installer
        ########################

        try:
            sub_message = f'create zip archive "{CONFIG.setup_zip_path_short}" of offline app installer "{CONFIG.setup_exe_path}" for notarization'
            #Functions.zip(CONFIG.setup_exe_path, CONFIG.setup_zip_path_short)
            Functions.run(
                'ditto',
                '-c',
                '-k',
                '--rsrc',
                '--sequesterRsrc',
                CONFIG.setup_exe_path,
                CONFIG.setup_zip_path_short)
        except Exception as sub_exception:
            Functions.printFailMessage(sub_message, sub_exception)
            sys.exit(1)
        else:
            Functions.printSuccessMessage(sub_message)

        try:
            sub_message = f'notarize app installer "{CONFIG.setup_zip_path_short}" for distribution outside of the Mac App Store' # Notarize the app by submitting a zipped package of the app bundle
            Functions.run(
                'xcrun', 'notarytool', 'submit',
                '--apple-id', APPSTORE_NOTARIZATION_USERNAME,
                '--team-id', TEAM_ID,
                '--password', APPSTORE_NOTARIZATION_PASSWORD,
                '--verbose',
                '--progress',
                '--wait',
                CONFIG.setup_zip_path_short)
        except Exception as sub_exception:
            Functions.printFailMessage(sub_message, sub_exception)
            sys.exit(1)
        else:
            Functions.printSuccessMessage(sub_message)

        try:
            sub_message = f'delete submitted zip "{CONFIG.setup_zip_path_short}" of notarized app installer'
            Functions.removeFile(CONFIG.setup_zip_path_short)
        except Exception as sub_exception:
            Functions.printFailMessage(sub_message, sub_exception)
            sys.exit(1)
        else:
            Functions.printSuccessMessage(sub_message)

        ######################
        # Staple app installer
        ######################

        try:
            sub_message = f'download and attach (staple) tickets for notarized executables to app installer "{CONFIG.setup_exe_path}"'
            time.sleep(180)  # Sleep for 3 minutes before calling the stapler to handle notarization lag on Apple server
                             # Or maybe one could instead get 'RequestUUID' from the previous 'xcrun altool --notarize-app...' output and
                             # check in the loop until notarization is succeded via 'xcrun altool --notarization-info UUID...'?
                             # If notarization is in progress, the '--notarization-info' output should contain 'Status: in progress'
                             # If notarization is succeded, the '--notarization-info' output should contain 'Status: success'
            Functions.run(
                'xcrun', 'stapler',
                'staple', CONFIG.setup_exe_path)
        except Exception as sub_exception:
            Functions.printFailMessage(sub_message, sub_exception)
            sys.exit(1)
        else:
            Functions.printSuccessMessage(sub_message)

        try:
            sub_message = f'verify the stapled tickets of app installer "{CONFIG.setup_exe_path}"'
            Functions.run(
                'xcrun', 'stapler',
                'validate', CONFIG.setup_exe_path)
        except Exception as sub_exception:
            Functions.printFailMessage(sub_message, sub_exception)
            sys.exit(1)
        else:
            Functions.printSuccessMessage(sub_message)

        try:
            sub_message = f'verify notarization of app installer "{CONFIG.setup_exe_path}"'
            Functions.run(
                'spctl',
                '--assess',
                '--verbose',
                CONFIG.setup_exe_path)
        except Exception as sub_exception:
            Functions.printFailMessage(sub_message, sub_exception)
            sys.exit(1)
        else:
            Functions.printSuccessMessage(sub_message)

    except Exception as exception:
        Functions.printFailMessage(message, exception)
        sys.exit(1)
    else:
        Functions.printSuccessMessage(message)


if __name__ == "__main__":
    if CONFIG.os == 'ubuntu':
        signLinux()
    elif CONFIG.os == 'windows':
        signWindows()
    elif CONFIG.os == 'macos':
        signMacos()
    else:
        raise AttributeError(f"OS '{CONFIG.os}' is not supported")
