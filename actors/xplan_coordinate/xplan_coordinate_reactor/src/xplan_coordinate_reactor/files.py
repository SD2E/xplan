"""Functions for uploading files to an agave path"""
from agavepy.actors import update_state
from attrdict import AttrDict
from .messagetypes import AbacoMessage
from reactors.runtime import Reactor, agaveutils
from requests.exceptions import HTTPError
import os
import time


# split an agave uri into (system_id, path)
def split_agave_uri(agave_uri: str) -> (str, str):
    if "agave://" not in agave_uri:
        raise Exception("agaveURI is not an agave URI: {}".format(agave_uri))
    # split the system id from the path
    return agave_uri.split("agave://")[1].split("/", 1)


def make_agave_uri(system_id: str, path: str) -> str:
    return "agave://{}/{}".format(system_id, path)


def download_file_from_system(r: Reactor, system_id: str, path: str, *, verbose=False, retrys=3, retry_delay=0.1):
    if verbose is True:
        r.logger.info("download {} from {}".format(path, system_id))
    try:
        return r.client.files.download(filePath=path, systemId=system_id)
    except Exception as exc:
        r.logger.error(exc)
        if retrys > 0:
            time.sleep(retry_delay)
            r.logger.info("retrying...\n  download {} from {}".format(path, system_id))
            download_file_from_system(r, system_id, path, verbose=False, retrys=retrys - 1, retry_delay=retry_delay)
        else:
            r.logger.error("Failed to download file! {}".format(make_agave_uri(system_id, path)))
            raise exc


def download_file(r: Reactor, downloadURI: str, *, verbose=False, retrys=3, retry_delay=0.1):
    system_id, path = split_agave_uri(downloadURI)
    return download_file_from_system(r, system_id, path, verbose=verbose, retrys=retrys, retry_delay=retry_delay)


def upload_file_to_system(r: Reactor, sourcePath: str, destSystem: str, destPath: str, *, name: str = None, verbose=False, retrys=3, retry_delay=0.1):
    try:
        with open(sourcePath, 'rb') as f:
            if name is None:
                if verbose is True:
                    r.logger.info("upload {} to {} on {}".format(sourcePath, destPath, destSystem))
                r.client.files.importData(filePath=destPath, systemId=destSystem, fileToUpload=f)
            else:
                if verbose is True:
                    r.logger.info("upload {} as {} to {} on {}".format(sourcePath, name, destPath, destSystem))
                r.client.files.importData(filePath=destPath, systemId=destSystem, fileName=name, fileToUpload=f)
    except Exception as exc:
        r.logger.error(exc)
        if retrys > 0:
            time.sleep(retry_delay)
            r.logger.info("retrying upload...")
            upload_file_to_system(r, sourcePath, destSystem, destPath, name=name, verbose=verbose, retrys=retrys - 1, retry_delay=retry_delay)
        else:
            r.logger.error("Failed to upload file! {} to {}".format(sourcePath, make_agave_uri(destSystem, destPath)))
            raise exc


def upload_file(r: Reactor, sourcePath: str, destinationURI: str, *, name: str = None, verbose=False, retrys=3, retry_delay=0.1):
    system_id, path = split_agave_uri(destinationURI)
    upload_file_to_system(r, sourcePath, system_id, path, name=name, verbose=verbose, retrys=retrys, retry_delay=retry_delay)


def ensure_path_on_system(r: Reactor, system_id: str, path: str, *, verbose=False, retrys=3, retry_delay=0.1):
    system_uri = "agave://{}/".format(system_id)
    mkdir(r, system_uri, path, verbose=verbose, retrys=retrys, retry_delay=retry_delay)


def ensure_agave_uri(r: Reactor, uri: str, *, verbose=False, retrys=3, retry_delay=0.1):
    system_id, path = split_agave_uri(uri)
    ensure_path_on_system(r, system_id, path, verbose=verbose, retrys=retrys, retry_delay=retry_delay)



def file_exists_on_system(r: Reactor, system_id: str, path: str, *, verbose=False, retrys=3, retry_delay=0.1):
    directory = os.path.dirname(path)
    filename = os.path.basename(path)
    contents = list_dir_on_system(r, system_id, directory, verbose=verbose, retrys=retrys, retry_delay=retry_delay)
    ls = [c['name'] for c in contents if c['type'] == 'file']
    if verbose is True:
        r.logger.info("Checking file_exists_on_system: {} on {}".format(path, system_id))
        r.logger.info("Searching for {} in {}".format(filename, ls))
    return filename in ls


def file_exists_at_agave_uri(r: Reactor, uri: str, *, verbose=False, retrys=3, retry_delay=0.1):
    system_id, path = split_agave_uri(uri)
    return file_exists_on_system(r, system_id, path, verbose=verbose, retrys=retrys, retry_delay=retry_delay)


def upload_dir(r: Reactor, sourceDir: str, destinationURI: str, *, verbose=False, retrys=3, retry_delay=0.1):
    system_id, destPath = split_agave_uri(destinationURI)

    # ensure the destinationURI exists at all
    ensure_path_on_system(r, system_id, destPath, verbose=verbose, retrys=retrys, retry_delay=retry_delay)

    # walk the soruceDir and upload each file to the destination
    # while making any needed directories along the way
    for (dirpath, dirnames, filenames) in os.walk(sourceDir):
        # we want the relative path when building agave uris
        relpath = os.path.relpath(dirpath, sourceDir)

        # make any directories we see
        for d in dirnames:
            if relpath == '.':
                path = d
            else:
                path = os.path.join(relpath, d)
            mkdir(r, destinationURI, path, verbose=verbose, retrys=retrys, retry_delay=retry_delay)

        # upload any files in the current directory
        for f in filenames:
            sourcePath = os.path.join(destPath, dirpath, f)

            if relpath == '.':
                path = destPath
            else:
                path = os.path.join(destPath, relpath)

            fileToUpload = make_agave_uri(system_id, path)
            upload_file(r, sourcePath, fileToUpload, verbose=verbose, retrys=retrys, retry_delay=retry_delay)


# files.manage(body=<BODY>, filePath=<FILEPATH>, systemId=<SYSTEMID>)
def mkdir_on_system(r: Reactor, system_id: str, path: str, dirpath: str, *, verbose=False, retrys=3, retry_delay=0.1):
    if verbose is True:
        r.logger.info("mkdir {} at {}".format(dirpath, make_agave_uri(system_id, path)))
    
    try:
        r.client.files.manage(systemId=system_id,
                              body={
                                  'action': 'mkdir',
                                  'path': dirpath
                              },
                              filePath=path)
    except Exception as exc:
        r.logger.error(exc)
        if retrys > 0:
            time.sleep(retry_delay)
            r.logger.info("retrying...\n  mkdir {} at {}".format(dirpath, make_agave_uri(system_id, path)))
            mkdir_on_system(r, system_id, path, dirpath, verbose=False, retrys=retrys - 1, retry_delay=retry_delay)
        else:
            r.logger.error("Failed to mkdir! {}".format(make_agave_uri(system_id, os.path.join(path, dirpath))))
            raise exc



def mkdir(r: Reactor, uri: str, dirpath: str, *, verbose=False, retrys=3, retry_delay=0.1):
    system_id, path = split_agave_uri(uri)
    mkdir_on_system(r, system_id, path, dirpath, verbose=verbose, retrys=retrys, retry_delay=retry_delay)


# files.list(filePath=<FILEPATH>, limit=250, offset=0, systemId=<SYSTEMID>)
def list_dir_on_system(r: Reactor, system_id: str, path: str, *, limit: int = 250, offset: int = 0, verbose=False, retrys=3, retry_delay=0.1):
    if verbose is True:
        r.logger.info("list: {}".format(make_agave_uri(system_id, path)))

    try:
        return r.client.files.list(filePath=path, limit=limit, offset=offset, systemId=system_id)
    except Exception as exc:
        r.logger.error(exc)
        if retrys > 0:
            time.sleep(retry_delay)
            r.logger.info("retrying...\n  list: {}".format(make_agave_uri(system_id, path)))
            return list_dir_on_system(r, system_id, path, limit=limit, offset=offset, verbose=False, retrys=retrys - 1, retry_delay=retry_delay)
        else:
            r.logger.error("Failed to listdir! {}".format(make_agave_uri(system_id, path)))
            raise exc


def list_dir(r: Reactor, uri: str, *, limit: int = 250, offset: int = 0, verbose=False, retrys=3, retry_delay=0.1):
    system_id, path = split_agave_uri(uri)
    return list_dir_on_system(r, system_id, path, limit=limit, offset=offset, verbose=verbose, retrys=retrys, retry_delay=retry_delay)


def collect_relative_file_paths(r: Reactor, uri: str, *, recursive=True, depth=0, max_depth=10, path=None, verbose=False, retrys=3, retry_delay=0.1):
    if verbose is True:
        r.logger.info("Collect files in {}".format(uri))
    # base results
    results = []

    # attempt to avoid infinite loops
    depth = max(0, depth)
    if depth > max_depth:
        r.logger.error("execute_on_dirs: max depth exceeded")
        return results

    # collect all files in the current dir
    contents = list_dir(r, uri, verbose=verbose, retrys=retrys, retry_delay=retry_delay)
    for file in contents:
        f = AttrDict(file)
        if f.type != 'file':
            continue
        if path is not None:
            results.append("{}/{}".format(path, f.name))
        else:
            results.append(f.name)

    # return early if we are not recursing through dirs
    if not recursive:
        return results

    # recurse into subdirectories
    for directory in contents:
        d = AttrDict(directory)
        if d.type != 'dir':
            continue
        if d.name == '.':
            continue
        if d.name == '..':
            continue
        next_uri = "{}/{}".format(uri, d.name)

        if path is not None:
            next_path = "{}/{}".format(path, d.name)
        else:
            next_path = d.name

        results += collect_relative_file_paths(
            r, next_uri,
            depth=depth+1,
            max_depth=max_depth,
            path=next_path,
            verbose=verbose,
            retrys=retrys,
            retry_delay=retry_delay)

    return results


def collect_file_paths(r: Reactor, uri: str, *, recursive=True, depth=0, max_depth=10, path=None, verbose=False, retrys=3, retry_delay=0.1):
    results = collect_relative_file_paths(
        r, uri, recursive=recursive, depth=depth, max_depth=max_depth, verbose=verbose, retrys=retrys, retry_delay=retry_delay)
    return ["{}/{}".format(uri, s) for s in results]


def download_dir(r: Reactor, downloadURI: str, destPath: str, *, recursive=True, makedirs=True, verbose=False, retrys=3, retry_delay=0.1):
    if verbose is True:
        r.logger.info("download_dir: {}".format(downloadURI))

    files = collect_relative_file_paths(r, downloadURI, recursive=recursive, verbose=verbose, retrys=retrys, retry_delay=retry_delay)
    for file in files:
        uri = "{}/{}".format(downloadURI, file)

        if verbose is True:
            r.logger.info("Download file: {}".format(uri))

        resp = download_file(r, uri, retrys=retrys, retry_delay=retry_delay)
        if not resp.ok:
            r.logger.error("Failed to download file: {}".format(uri))
            continue

        directory = os.path.dirname(file)
        out_dir = os.path.join(destPath, directory)
        if not os.path.exists(out_dir):
            if makedirs is True:
                os.makedirs(out_dir)
            else:
                r.logger.error("Missing output directory: {}".format(out_dir))
                continue

        out_path = os.path.join(out_dir, os.path.basename(file))
        with open(out_path, 'wb') as f:
            f.write(resp.content)
            if verbose is True:
                r.logger.info("Wrote file: {}".format(out_path))

