# A small Install CommandData.
# This will pip install the LZ4 module.
# If no Python LZ4 module in C4D, this is the only registered command.
# After successful installation and a restart of Cinema 4D,
# the regular Rokoko Studio Live plugin modules will be registered.
import sys, os, importlib, subprocess
import c4d

from rokoko_ids import *
from rokoko_dialog_question import *


class CommandDataRokokoInstall(c4d.plugins.CommandData):

    def Execute(self, doc):
        versionC4DMajor = c4d.GetC4DVersion() // 1000

        # We only support Cinema 4D versions with Python 3, so R23+
        if versionC4DMajor < 23:
            msg = [ ('Unfortunately your version of Cinema 4D is not supported.', c4d.BORDER_WITH_TITLE_BOLD),
                    '',
                    'Minimum version required: R23'
                  ]

            OpenErrorDialog(msgs=msg, icon=DQ_ICON_ERROR)

            return True

        lz4Loader = importlib.util.find_spec('lz4')

        if lz4Loader is not None:
            # If we are here, it means there is an LZ4 module in Python available.
            # Yet, we are here, which means ther user has not yet restarted C4D,
            # because otherwise this CommandData would not have been registered at all.
            msg = [ 'It seems installation has been run before, but Cinema 4D needs a restart.',
                    '',
                    'Please restart Cinema 4D, now.'
                  ]

            OpenInfoDialog(msgs=msg)

            return True

        msg = [ 'Installation takes a few seconds.',
                'Cinema 4D will seem frozen during this time.',
                '',
                'Do you want to start installation, now?'
              ]

        result = OpenYesNoDialog(msgs=msg)
        if result == DQ_RESULT_NO:
            return True

        # Determine the installation path.
        # Begin with the path common in all Cinema 4D installations.
        basedir = __file__[:__file__.rfind(os.sep)]
        sys.path.insert(0, basedir)
        currentOS = c4d.GeGetCurrentOS()
        pathPython = os.path.join(c4d.storage.GeGetStartupPath(), 'resource', 'modules', 'python', 'libs')

        # Depending on Cinema 4D version and OS version,
        # the next sub-directory and also the name of the Python executable differ.
        # Also we need to choose a LZ4 module version available as binary package for the respective OS/C4D combination.
        if versionC4DMajor == 23:
            versionPython = '37'
            versionLZ4 = '3.0.1'

        elif versionC4DMajor == 24:
            versionPython = '39'
            versionLZ4 = '3.1.3'

        elif versionC4DMajor >= 25:
            versionPython = '39'
            versionLZ4 = '3.1.3'

        if currentOS == c4d.OPERATINGSYSTEM_WIN:
            pathPython = os.path.join(pathPython, 'python{0}.win64.framework'.format(versionPython))
            pathPythonExec = os.path.join(pathPython, 'python.exe')

        elif currentOS == c4d.OPERATINGSYSTEM_OSX:
            pathPython = os.path.join(pathPython, 'python{0}.macos.framework'.format(versionPython))
            pathPythonExec = os.path.join(pathPython, 'python')

        else:
            msg = [ ('Unfortunately your OS is not supported.', c4d.BORDER_WITH_TITLE_BOLD) ]

            OpenErrorDialog(msgs=msg, icon=DQ_ICON_ERROR)

            return True

        # First ensure, pip is installed.
        command = '"' + pathPythonExec + '" -m ensurepip --default-pip'
        try:
            proc = subprocess.Popen(command, shell=True, cwd=pathPython,
                                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        except:
            pass # deliberately surpressing any exception

        if proc is None or proc.poll() is not None:
            msg = [ ('Failed to install pip!', c4d.BORDER_WITH_TITLE_BOLD) ]

            OpenErrorDialog(msgs=msg, icon=DQ_ICON_ERROR)

            return True

        stdout, stderr = proc.communicate()
        # TODO Andreas: Check the console output for success
        #result = str(stdout[:])

        #if 'Requirement already satisfied' not in result:
        #    print(stdout[:80])
        #    print(result)
        #    c4d.gui.MessageDialog('Rokoko Studio Live:\nFAILED to install pip!', type=c4d.GEMB_ICONEXCLAMATION)
        #    return True

        # Then install the actual LZ4 module.
        command = '"' + pathPythonExec + '" -m pip install lz4=={0}'.format(versionLZ4)
        try:
            proc = subprocess.Popen(command, shell=True, cwd=None,
                                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT)

        except:
            pass # deliberately surpressing any exception

        if proc is None or proc.poll() is not None:
            msg = [ ('FAILED to install LZ4!', c4d.BORDER_WITH_TITLE_BOLD) ]

            OpenErrorDialog(msgs=msg, icon=DQ_ICON_ERROR)

            return True

        stdout, stderr = proc.communicate()
        result = str(stdout[:])

        if 'Successfully installed lz4-' not in result:
            print(stdout[:80])
            print(stdout[-80:])
            print(result)
            msg = [ ('FAILED to install LZ4!', c4d.BORDER_WITH_TITLE_BOLD),
                    '',
                    'Please send output printed to Console to our support.'
                  ]

            OpenErrorDialog(msgs=msg, icon=DQ_ICON_ERROR)

            return True

        msg = [ ('Installation successful.', c4d.BORDER_WITH_TITLE_BOLD),
                '',
                'Cinema 4D needs to be restarted for the plugin to be loaded.',
                '',
                'Please restart Cinema 4D, now.'
              ]

        OpenInfoDialog(msgs=msg)

        # Would be cool to offer application restart to user, but
        # unfortunately in later versions of C4D c4d.RestartMe() does no longer reliably work.
        # It either does not restart C4D or crashes the application on exit...

        return True
