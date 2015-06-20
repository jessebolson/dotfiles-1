#!/usr/bin/env python
# encoding: utf-8
#
# To execute this test requires two terminals, one for running Vim and one
# for executing the test script. Both terminals should have their current
# working directories set to this directory (the one containing this
# test_all.py script).
#
# In one terminal, launch a tmux session named ``vim``:
#   $ tmux new -s vim
#
# Now, from another terminal, launch the testsuite:
#    $ ./test_all.py
#
# Note: if you want to use Vim against the Python 3 bindings, you must launch the
# test suite using Python 3.  For example:
#    $ python3 ./test_all.py
#
# For each test, the test_all.py script will launch vim with a vimrc, run the
# test, compare the output and exit vim again. The keys are send using tmux send-keys.
#
# To limit the tests that are executed, specify a pattern to be used to match
# the beginning of the test name.  For instance, the following will execute all
# tests that start with "SimpleExpand":
#    $ ./test_all.py SimpleExpand
#
# NOTE: The test suite is not working under Windows right now as I have no
# access to a windows system for fixing it. Volunteers welcome. Here are some
# comments from the last time I got the test suite running under windows.
#
# Under windows, COM's SendKeys is used to send keystrokes to the gvim window.
# Note that Gvim must use english keyboard input (choose in windows registry)
# for this to work properly as SendKeys is a piece of chunk. (i.e. it sends
# <F13> when you send a | symbol while using german key mappings)

# pylint: skip-file

import os
import platform
import subprocess
import unittest
from test.vim_interface import (create_directory, tempfile, VimInterfaceTmux)


def plugin_cache_dir():
    """The directory that we check out our bundles to."""
    return os.path.join(tempfile.gettempdir(), 'UltiSnips_test_vim_plugins')


def clone_plugin(plugin):
    """Clone the given plugin into our plugin directory."""
    dirname = os.path.join(plugin_cache_dir(), os.path.basename(plugin))
    print('Cloning %s -> %s' % (plugin, dirname))
    if os.path.exists(dirname):
        print('Skip cloning of %s. Already there.' % plugin)
        return
    create_directory(dirname)
    subprocess.call(['git', 'clone', '--recursive',
                     '--depth', '1', 'https://github.com/%s' % plugin, dirname])

    if plugin == 'Valloric/YouCompleteMe':
        # CLUTCH: this plugin needs something extra.
        subprocess.call(os.path.join(dirname, './install.sh'), cwd=dirname)


def setup_other_plugins(all_plugins):
    """Creates /tmp/UltiSnips_test_vim_plugins and clones all plugins into
    this."""
    clone_plugin('tpope/vim-pathogen')
    for plugin in all_plugins:
        clone_plugin(plugin)

if __name__ == '__main__':
    import optparse
    import sys

    def parse_args():
        p = optparse.OptionParser('%prog [OPTIONS] <test case names to run>')

        p.set_defaults(session='vim', interrupt=False,
                       verbose=False, retries=4, plugins=False)

        p.add_option('-v', '--verbose', dest='verbose', action='store_true',
                     help='print name of tests as they are executed')
        p.add_option('--clone-plugins', action='store_true',
                     help='Only clones dependant plugins and exits the test runner.')
        p.add_option('--plugins', action='store_true',
                     help='Run integration tests with other Vim plugins.')
        p.add_option('-s', '--session', dest='session', metavar='SESSION',
                     help='session parameters for the terminal multiplexer SESSION [%default]')
        p.add_option('-i', '--interrupt', dest='interrupt',
                     action='store_true',
                     help='Stop after defining the snippet. This allows the user '
                     'to interactively test the snippet in vim. You must give '
                     'exactly one test case on the cmdline. The test will always fail.'
                     )
        p.add_option('-r', '--retries', dest='retries', type=int,
                     help='How often should each test be retried before it is '
                     'considered failed. Works around flakyness in the terminal '
                     'multiplexer and race conditions in writing to the file system.')
        p.add_option('-x', '--exitfirst', dest='exitfirst', action='store_true',
                     help='exit instantly on first error or failed test.')

        o, args = p.parse_args()
        return o, args

    def flatten_test_suite(suite):
        flatten = unittest.TestSuite()
        for test in suite:
            if isinstance(test, unittest.TestSuite):
                flatten.addTests(flatten_test_suite(test))
            else:
                flatten.addTest(test)
        return flatten

    def main():
        options, selected_tests = parse_args()

        all_test_suites = unittest.defaultTestLoader.discover(start_dir='test')

        vim = VimInterfaceTmux(options.session)
        if not options.clone_plugins and platform.system() == 'Windows':
            raise RuntimeError(
                'TODO: TestSuite is broken under windows. Volunteers wanted!.')
            # vim = VimInterfaceWindows()
            # vim.focus()

        all_other_plugins = set()

        tests = set()
        suite = unittest.TestSuite()

        for test in flatten_test_suite(all_test_suites):
            test.interrupt = options.interrupt
            test.retries = options.retries
            test.test_plugins = options.plugins
            test.vim = vim
            all_other_plugins.update(test.plugins)

            if len(selected_tests):
                id = test.id().split('.')[1]
                if not any([id.startswith(t) for t in selected_tests]):
                    continue
            tests.add(test)
        suite.addTests(tests)

        if options.plugins or options.clone_plugins:
            setup_other_plugins(all_other_plugins)
            if options.clone_plugins:
                return

        v = 2 if options.verbose else 1
        successfull = unittest.TextTestRunner(verbosity=v,
                                          failfast=options.exitfirst).run(suite).wasSuccessful()
        return 0 if successfull else 1
    sys.exit(main())

# vim:fileencoding=utf-8:foldmarker={{{#,#}}}:
