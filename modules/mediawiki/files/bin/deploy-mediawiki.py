#! /usr/bin/python3

from __future__ import annotations

import argparse
import os
import socket
import subprocess
import time
from sys import exit
from typing import TypedDict

from langcodes import tag_is_valid

import requests


repos = {'config': 'config', 'world': 'w', 'landing': 'landing', 'errorpages': 'ErrorPages'}
DEPLOYUSER = 'www-data'


class Environment(TypedDict):
    wikidbname: str
    wikiurl: str
    servers: list


class EnvironmentList(TypedDict):
    beta: Environment
    prod: Environment


class ProcessList(TypedDict):
    operations: list[subprocess.Popen]


class WikiCommand:
    def __init__(self, command: str, wiki: str) -> None:
        self = f'sudo -u {DEPLOYUSER} {command} --wiki={wiki}'  # noqa: F841

    def __str__(self):
        return f'{self}'


beta: Environment = {
    'wikidbname': 'betawiki',
    'wikiurl': 'beta.betaheze.org',
    'servers': ['test101'],
}
prod: Environment = {
    'wikidbname': 'testwiki',  # don't use loginwiki anymore - we want this to be an experimental wiki
    'wikiurl': 'publictestwiki.com',
    'servers': ['mw101', 'mw102', 'mw111', 'mw112', 'mw121', 'mw122', 'mwtask111'],
}
ENVIRONMENTS: EnvironmentList = {
    'beta': beta,
    'prod': prod,
}
del beta
del prod
HOSTNAME = socket.gethostname().split('.')[0]


def get_command_array(command: str | WikiCommand) -> list[str]:
    arraycommand = str(command).split(' ')
    commandfile = arraycommand[0]
    arraycommand.remove(commandfile)
    commandopts = ' '.join(arraycommand)
    return [commandfile, commandopts]


def get_environment_info() -> Environment:
    if HOSTNAME.startswith('test'):
        return ENVIRONMENTS['beta']
    return ENVIRONMENTS['prod']


def get_server_list(envinfo: Environment, servers: str) -> list[str]:
    if servers in ('all', 'scsvg'):
        return envinfo['servers']
    return servers.split(',')


def run_batch_command(commands: list[str] | list[WikiCommand], tag: str, exitcodes: list[int]) -> list[int]:
    processes: ProcessList = {'operations': []}
    print(f'Start {tag} commands.')
    for operation in commands:
        normalised_command = get_command_array(operation)
        print(f'Scheduling {operation}')
        pop = subprocess.Popen(normalised_command)
        processes['operations'].append(pop)
    for p in processes['operations']:
        p.wait()
        print(f'Completed {p} (Exit:{p.returncode})')
        exitcodes.append(p.returncode)
    print(f'completed {tag} commands')
    return exitcodes


def run_command(cmd: str | WikiCommand) -> int:
    start = time.time()
    print(f'Execute: {cmd}')
    ec = os.system(str(cmd))
    print(f'Completed ({ec}) in {str(int(time.time() - start))}s!')
    return ec


def non_zero_code(ec: list[int], nolog: bool = True, leave: bool = True) -> bool:
    for code in ec:
        if code != 0:
            if not nolog:
                os.system('/usr/local/bin/logsalmsg DEPLOY ABORTED: Non-Zero Exit Code in prep, see output.')
            if leave:
                print('Exiting due to non-zero status.')
                exit(1)
            return True
    return False


def check_up(nolog: bool, Debug: str | None = None, Host: str | None = None, domain: str = 'meta.miraheze.org', verify: bool = True, force: bool = False, port: int = 443) -> bool:
    if not Debug and not Host:
        raise Exception('Host or Debug must be specified')
    if Debug:
        server = f'{Debug}.miraheze.org'
        headers = {'X-Miraheze-Debug': server}
        location = f'{domain}@{server}'
    else:
        os.environ['NO_PROXY'] = 'localhost'
        domain = 'localhost'
        headers = {'host': f'{Host}'}
        location = f'{Host}@{domain}'
    up = False
    if port == 443:
        proto = 'https://'
    else:
        proto = 'http://'
    req = requests.get(f'{proto}{domain}:{port}/w/api.php?action=query&meta=siteinfo&formatversion=2&format=json', headers=headers, verify=verify)
    if req.status_code == 200 and 'miraheze' in req.text and (Debug is None or Debug in req.headers['X-Served-By']):
        up = True
    if not up:
        print(f'Status: {req.status_code}')
        print(f'Text: {"miraheze" in req.text} \n {req.text}')
        if 'X-Served-By' not in req.headers:
            req.headers['X-Served-By'] = 'None'
        print(f'Debug: {(Debug is None or Debug in req.headers["X-Served-By"])}')
        if force:
            print(f'Ignoring canary check error on {location} due to --force')
        else:
            print(f'Canary check failed for {location}. Aborting... - use --force to proceed')
            message = f'/usr/local/bin/logsalmsg DEPLOY ABORTED: Canary check failed for {location}'
            if nolog:
                print(message)
            else:
                os.system(message)
            exit(3)
    return up


def remote_sync_file(time: str, serverlist: list[str], path: str, exitcodes: list[int], recursive: bool = True) -> list[int]:
    print(f'Start {path} deploys to {serverlist}.')
    sync_cmds = []
    for server in serverlist:
        if HOSTNAME != server.split('.')[0]:
            print(f'Scheduling {path} for {server}.')
            sync_cmds.append(_construct_rsync_command(time=time, local=False, dest=path, server=server, recursive=recursive))
        else:
            continue
    ec = run_batch_command(sync_cmds, 'remote sync', exitcodes)
    print(f'Finished {path} deploys to {serverlist}.')
    return ec  # noqa: R504


def _get_staging_path(repo: str) -> str:
    return f'/srv/mediawiki-staging/{repos[repo]}/'


def _get_deployed_path(repo: str) -> str:
    return f'/srv/mediawiki/{repos[repo]}/'


def _construct_rsync_command(time: str, dest: str, recursive: bool = True, local: bool = True, location: None | str = None, server: None | str = None) -> str:
    if time:
        params = '--inplace'
    else:
        params = '--update'
    if recursive:
        params = params + ' -r --delete'
    if local:
        if location is None:
            raise Exception('Location must be specified for local rsync.')
        return f'sudo -u {DEPLOYUSER} rsync {params} --exclude=".*" {location} {dest}'
    if location is None:
        location = dest
    if location == dest and server:  # ignore location if not specified, if given must equal dest.
        return f'sudo -u {DEPLOYUSER} rsync {params} -e "ssh -i /srv/mediawiki-staging/deploykey" {dest} {DEPLOYUSER}@{server}.miraheze.org:{dest}'
    # a return None here would be dangerous - except and ignore R503 as return after Exception is not reachable
    raise Exception(f'Error constructing command. Either server was missing or {location} != {dest}')  # noqa: R503


def _construct_git_pull(repo: str, submodules: bool = False, branch: str | None = None) -> str:
    extrap = ' '
    if submodules:
        extrap += '--recurse-submodules '

    if branch:
        extrap += f'origin {branch} '

    return f'sudo -u {DEPLOYUSER} git -C {_get_staging_path(repo)} pull{extrap}--quiet'


def run(args: argparse.Namespace, start: float) -> int:
    envinfo = get_environment_info()
    servers = get_server_list(envinfo, args.servers)
    options = {'config': args.config, 'world': args.world, 'landing': args.landing, 'errorpages': args.errorpages}
    exitcodes: list[int] = []
    loginfo = {}
    rsyncpaths: list[str] = []
    rsyncfiles: list[str] = []
    rsync: list[str] = []
    rebuild: list[WikiCommand] = []
    postinstall: list[WikiCommand] = []
    stage: list[str] = []
    for arg in vars(args).items():
        if arg[1] is not None and arg[1] is not False:
            loginfo[arg[0]] = arg[1]
    synced = loginfo['servers']
    if HOSTNAME in servers:
        del loginfo['servers']
        text = f'starting deploy of "{str(loginfo)}" to {synced}'
        if not args.nolog:
            os.system(f'/usr/local/bin/logsalmsg {text}')
        else:
            print(text)
        pull = []
        if args.world and not args.pull:
            pull = ['world']
        if args.pull:
            pull = str(args.pull).split(',')
        if args.world and 'world' not in pull:
            pull.append('world')
        if pull:
            for repo in pull:
                if repo == 'world':
                    sm = True
                else:
                    sm = False
                try:
                    stage.append(_construct_git_pull(repo, submodules=sm, branch=args.branch))
                except KeyError:
                    print(f'Failed to pull {repo} due to invalid name')

        # setup env, git pull etc
        exitcodes = run_batch_command(stage, 'staging', exitcodes)
        non_zero_code(exitcodes, nolog=args.nolog, leave=(not args.force))
        for option in options:  # configure rsync & custom data for repos
            if options[option]:
                if option == 'world':  # install steps for w
                    os.chdir(_get_staging_path('world'))
                    exitcodes.append(run_command(f'sudo -u {DEPLOYUSER} http_proxy=http://bast.miraheze.org:8080 composer install --no-dev --quiet'))
                    rebuild.append(WikiCommand('MW_INSTALL_PATH=/srv/mediawiki-staging/w php /srv/mediawiki-staging/w/extensions/MirahezeMagic/maintenance/rebuildVersionCache.php --save-gitinfo --conf=/srv/mediawiki-staging/config/LocalSettings.php', envinfo['wikidbname']))
                    rsyncpaths.append('/srv/mediawiki/cache/gitinfo/')
                rsync.append(_construct_rsync_command(time=args.ignoretime, location=f'{_get_staging_path(option)}*', dest=_get_deployed_path(option)))
        non_zero_code(exitcodes, nolog=args.nolog, leave=(not args.force))
        if args.files:  # specfic extra files
            files = str(args.files).split(',')
            for file in files:
                rsync.append(_construct_rsync_command(time=args.ignoretime, recursive=False, location=f'/srv/mediawiki-staging/{file}', dest=f'/srv/mediawiki/{file}'))
        if args.folders:  # specfic extra folders
            folders = str(args.folders).split(',')
            for folder in folders:
                rsync.append(_construct_rsync_command(time=args.ignoretime, location=f'/srv/mediawiki-staging/{folder}/*', dest=f'/srv/mediawiki/{folder}/'))

        if args.extensionlist:  # when adding skins/exts
            rebuild.append(WikiCommand('/srv/mediawiki/w/extensions/CreateWiki/maintenance/rebuildExtensionListCache.php', envinfo['wikidbname']))

        # move staged content to live
        exitcodes = run_batch_command(rsync, 'rsync', exitcodes)
        non_zero_code(exitcodes, nolog=args.nolog, leave=(not args.force))
        # These need to be setup late because dodgy
        if args.l10n:  # setup l10n
            if args.lang:
                for language in str(args.lang).split(','):
                    if not tag_is_valid(language):
                        raise ValueError(f'{language} is not a valid language.')

                lang = f'--lang={args.lang}'
            else:
                lang = ''

            postinstall.append(WikiCommand('/srv/mediawiki/w/maintenance/mergeMessageFileList.php --quiet --output /srv/mediawiki/config/ExtensionMessageFiles.php', envinfo['wikidbname']))
            rebuild.append(WikiCommand(f'/srv/mediawiki/w/maintenance/rebuildLocalisationCache.php {lang} --quiet', envinfo['wikidbname']))

        # cmds to run after rsync & install (like mergemessage)
        exitcodes = run_batch_command(postinstall, 'post-install', exitcodes)
        non_zero_code(exitcodes, nolog=args.nolog, leave=(not args.force))
        # update ext list + l10n
        exitcodes = run_batch_command(rebuild, 'rebuild', exitcodes)
        non_zero_code(exitcodes, nolog=args.nolog, leave=(not args.force))

        # see if we are online - exit code 3 if not
        if args.port:
            check_up(Debug=None, Host=envinfo['wikiurl'], verify=False, force=args.force, nolog=args.nolog, port=args.port)
        else:
            check_up(Debug=None, Host=envinfo['wikiurl'], verify=False, force=args.force, nolog=args.nolog)

    # actually set remote lists
    for option in options:
        if options[option]:
            rsyncpaths.append(_get_deployed_path(option))
    if args.files:
        for file in str(args.files).split(','):
            rsyncfiles.append(f'/srv/mediawiki/{file}')
    if args.folders:
        for folder in str(args.folders).split(','):
            rsyncpaths.append(f'/srv/mediawiki/{folder}/')
    if args.extensionlist:
        rsyncfiles.append('/srv/mediawiki/cache/extension-list.json')
    if args.l10n:
        rsyncpaths.append('/srv/mediawiki/cache/l10n/')

    for path in rsyncpaths:
        exitcodes = remote_sync_file(time=args.ignoretime, serverlist=servers, path=path, exitcodes=exitcodes)
    for file in rsyncfiles:
        exitcodes = remote_sync_file(time=args.ignoretime, serverlist=servers, path=file, exitcodes=exitcodes, recursive=False)

    fintext = f'finished deploy of "{str(loginfo)}" to {synced}'

    failed = non_zero_code(ec=exitcodes, leave=False)
    if failed:
        fintext += f' - FAIL: {exitcodes}'
    else:
        fintext += ' - SUCCESS'
    fintext += f' in {str(int(time.time() - start))}s'
    if not args.nolog:
        os.system(f'/usr/local/bin/logsalmsg {fintext}')
    else:
        print(fintext)
    if failed:
        return 1
    return 0


if __name__ == '__main__':
    start = time.time()
    parser = argparse.ArgumentParser(description='Process some integers.')
    parser.add_argument('--pull', dest='pull')
    parser.add_argument('--branch', dest='branch')
    parser.add_argument('--config', dest='config', action='store_true')
    parser.add_argument('--world', dest='world', action='store_true')
    parser.add_argument('--landing', dest='landing', action='store_true')
    parser.add_argument('--errorpages', dest='errorpages', action='store_true')
    parser.add_argument('--l10n', dest='l10n', action='store_true')
    parser.add_argument('--extension-list', dest='extensionlist', action='store_true')
    parser.add_argument('--no-log', dest='nolog', action='store_true')
    parser.add_argument('--force', dest='force', action='store_true')
    parser.add_argument('--files', dest='files')
    parser.add_argument('--folders', dest='folders')
    parser.add_argument('--lang', dest='lang')
    parser.add_argument('--servers', dest='servers', required=True)
    parser.add_argument('--ignore-time', dest='ignoretime', action='store_true')
    parser.add_argument('--port', dest='port')

    exit(run(parser.parse_args(), start))
