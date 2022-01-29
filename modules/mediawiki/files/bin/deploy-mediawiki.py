#! /usr/bin/python3

import argparse
import os
import time
import requests


repos = {'config': 'config', 'world': 'w', 'landing': 'landing', 'errorpages': 'ErrorPages'}
DEPLOYUSER = 'www-data'


def run_command(cmd):
    start = time.time()
    print(f'Execute: {cmd}')
    ec = os.system(cmd)
    print(f'Completed ({ec}) in {str(int(time.time() - start))}s!')
    return ec


def non_zero_code(ec, exit=True):
    for code in ec:
        if code != 0:
            if exit:
                print('Exiting due to non-zero status.')
                exit(1)
            return True
    return False


def check_up(Debug=None, Host=None, domain='https://meta.miraheze.org', verify=True, force=False):
    if not Debug and not Host:
        raise Exception('Host or Debug must be specified')
    if Debug:
        server = f'{Debug}.miraheze.org'
        headers = {'X-Miraheze-Debug': server}
        location = f'{domain}@{server}'
    else:
        os.environ['NO_PROXY'] = 'localhost'
        domain = 'https://localhost'
        headers = {'host': Host}
        location = f'{Host}@{domain}'
    up = False
    print(headers)
    print(f'{domain}/w/api.php?action=query&meta=siteinfo&formatversion=2&format=json')
    req = requests.get(f'{domain}/w/api.php?action=query&meta=siteinfo&formatversion=2&format=json', headers=headers, verify=verify)
    if req.status_code == 200 and 'miraheze' in req.text and (Debug is None or Debug in req.headers['X-Served-By']):
        up = True
    if not up:
        print(f'Status: {req.status_code}')
        print(f'Text: {"miraheze" in req.text}')
        print(f'Debug: {(Debug is None or Debug in req.headers["X-Served-By"])}')
        if force:
            print(f'Ignoring canary check error on {location} due to --force')
        else:
            print(f'Canary check failed for {location}. Aborting... - use --force to proceed')
            os.system(f'/usr/local/bin/logsalmsg DEPLOY ABORTED: Canary check failed for {location}')
            exit(3)
    return up

def remote_sync_file(time, serverlist, path, recursive=True, force=False):
    print(f'Start {path} deploys.')
    for server in serverlist:
        print(f'Deploying {path} to {server}.')
        ec = run_command(_construct_rsync_command(time=time, local=False, dest=path, server=server, recursive=recursive))
        check_up(Debug=server, force=force)
        print(f'Deployed {path} to {server}.')
    print(f'Finished {path} deploys.')
    return ec


def _get_staging_path(repo):
    return f'/srv/mediawiki-staging/{repos[repo]}/'


def _get_deployed_path(repo):
    return f'/srv/mediawiki/{repos[repo]}/'


def _construct_rsync_command(time, dest, recursive=True, local=True, location=None, server=None):
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
    else:
        raise Exception(f'Error constructing command. Either server was missing or {location} != {dest}')


def _construct_git_pull(repo, submodules=False):
    if submodules:
        extrap = '--recurse-submodules'
    else:
        extrap = ''
    return f'sudo -u {DEPLOYUSER} git -C {_get_staging_path(repo)} pull {extrap} --quiet'


def run(args, start):
    loginfo = {}
    exitcodes = []
    for arg in vars(args).items():
        if arg[1] is not None and arg[1] is not False:
            loginfo[arg[0]] = arg[1]
    synced = loginfo['servers']
    del loginfo['servers']
    text = f'starting deploy of "{str(loginfo)}" to {synced}'
    rsyncpaths = []
    rsyncfiles = []
    rsync = []
    rebuild = []
    postinstall = []
    stage = []
    if not args.nolog:
        os.system(f'/usr/local/bin/logsalmsg {text}')
    else:
        print(text)
    if args.world and not args.pull:
        pull = ['world']
    if args.pull or args.world:
        if args.pull:
            pull = str(args.pull).split(',')
        elif args.world and 'world' not in pull:
            pull.append('world')
        for repo in pull:
            if repo == 'world':
                sm = True
            else:
                sm = False
            try:
                stage.append(_construct_git_pull(repo, submodules=sm))
            except KeyError:
                print(f'Failed to pull {repo} due to invalid name')

    options = {'config': args.config, 'world': args.world, 'landing': args.landing, 'errorpages': args.errorpages}
    for cmd in stage:  # setup env, git pull etc
        exitcodes.append(run_command(cmd))
    non_zero_code(exitcodes)
    for option in options:  # configure rsync & custom data for repos
        if options[option]:
            if option == 'world':  # install steps for w
                os.chdir(_get_staging_path('world'))
                exitcodes.append(run_command('sudo -u www-data composer install --no-dev --quiet'))
                rebuild.append('sudo -u www-data php /srv/mediawiki/w/extensions/MirahezeMagic/maintenance/rebuildVersionCache.php --save-gitinfo --wiki=loginwiki')
                rsyncpaths.append('/srv/mediawiki/cache/gitinfo/')
            rsync.append(_construct_rsync_command(time=args.ignoretime, location=f'{_get_staging_path(option)}*', dest=_get_deployed_path(option)))
            rsyncpaths.append(_get_deployed_path(option))
    non_zero_code(exitcodes)
    if args.files:  # specfic extra files
        files = str(args.files).split(',')
        for file in files:
            rsync.append(_construct_rsync_command(time=args.ignoretime, recursive=False, location=f'/srv/mediawiki-staging/{file}', dest=f'/srv/mediawiki/{file}'))
            rsyncfiles.append(f'/srv/mediawiki/{file}')
    if args.folders:  # specfic extra folders
        folders = str(args.folders).split(',')
        for folder in folders:
            rsync.append(_construct_rsync_command(time=args.ignoretime, location=f'/srv/mediawiki-staging/{folder}/*', dest='/srv/mediawiki/{folder}/'))
            rsyncpaths.append(f'/srv/mediawiki/{folder}/')

    if args.extensionlist:  # when adding skins/exts
        rebuild.append('sudo -u www-data php /srv/mediawiki/w/extensions/CreateWiki/maintenance/rebuildExtensionListCache.php --wiki=loginwiki')
        rsyncfiles.append('/srv/mediawiki/cache/extension-list.json')

    for cmd in rsync:  # move staged content to live
        exitcodes.append(run_command(cmd))
    non_zero_code(exitcodes)
    # These need to be setup late because dodgy
    if args.l10nupdate:  # used by automated maint
        run_command('sudo -u www-data ionice -c idle /usr/bin/nice -n 15 /usr/bin/php /srv/mediawiki/w/extensions/LocalisationUpdate/update.php --wiki=loginwiki')  # gives garbage errors
        args.l10n = True  # imply --l10n
    if args.l10n:  # setup l10n
        postinstall.append('sudo -u www-data php /srv/mediawiki/w/maintenance/mergeMessageFileList.php --quiet --wiki=loginwiki --output /srv/mediawiki/config/ExtensionMessageFiles.php')
        rebuild.append('sudo -u www-data php /srv/mediawiki/w/maintenance/rebuildLocalisationCache.php --quiet --wiki=loginwiki')
        rsyncpaths.append('/srv/mediawiki/cache/l10n/')

    for cmd in postinstall:  # cmds to run after rsync & install (like mergemessage)
        exitcodes.append(run_command(cmd))
    non_zero_code(exitcodes)
    for cmd in rebuild:  # update ext list + l10n
        exitcodes.append(run_command(cmd))
    non_zero_code(exitcodes)

    # see if we are online - exit code 3 if not
    check_up(Debug=None, Host='beta.betaheze.org', verify=False, force=args.force)

    # decide what servers to remote on
    sync = True
    if args.servers == 'skip':
        sync = False
        print('Sync skipped. Mediawiki deploy has not passed canary stage.')
    elif args.servers in ('all', 'scsvg'):
        serverlist = ['mw101', 'mw102', 'mw111', 'mw112', 'mw121', 'mw122']
    else:
        serverlist = str(args.servers).split(',')

    if sync:
        for path in rsyncpaths:
            exitcodes.append(remote_sync_file(time=args.ignoretime, serverlist=serverlist, path=path, force=args.force))
        for file in rsyncfiles:
            exitcodes.append(remote_sync_file(time=args.ignoretime, serverlist=serverlist, path=file, recursive=False, force=args.force))

    fintext = f'finished deploy of "{str(loginfo)}" to {synced}'

    failed = non_zero_code(ec=exitcodes, exit=False)
    if failed:
        fintext += ' - FAIL: {exitcodes}'
    else:
        fintext += ' - SUCCESS'
    fintext += f' in {str(int(time.time() - start))}s'
    if not args.nolog:
        os.system(f'/usr/local/bin/logsalmsg {fintext}')
    else:
        print(fintext)
    if failed:
        exit(1)


if __name__ == '__main__':
    start = time.time()
    parser = argparse.ArgumentParser(description='Process some integers.')
    parser.add_argument('--pull', dest='pull')
    parser.add_argument('--config', dest='config', action='store_true')
    parser.add_argument('--world', dest='world', action='store_true')
    parser.add_argument('--landing', dest='landing', action='store_true')
    parser.add_argument('--errorpages', dest='errorpages', action='store_true')
    parser.add_argument('--l10nupdate', dest='l10nupdate', action='store_true')
    parser.add_argument('--l10n', dest='l10n', action='store_true')
    parser.add_argument('--extension-list', dest='extensionlist', action='store_true')
    parser.add_argument('--no-log', dest='nolog', action='store_true')
    parser.add_argument('--force', dest='force', action='store_true')
    parser.add_argument('--files', dest='files')
    parser.add_argument('--folders', dest='folders')
    parser.add_argument('--servers', dest='servers', required=True)
    parser.add_argument('--ignore-time', dest='ignoretime', action='store_true')

    run(parser.parse_args(), start)