#!/usr/bin/env python

import requests
import json
import os
import errno
import datetime
import tempfile

UNAME ='mozilla'
GITHUB_HOSTNAME='https://api.github.com'

class GitHub(object):
    def __init__(self, username):
        self.username = username
        self.backup_dir = './backups/%s' % username 

    def _api(self, http_path, last_backup):
        url = '%s/%s' % (GITHUB_HOSTNAME, http_path)
        h = requests.head(url)
        if 'last-modified' in h.headers:
            last_modified = datetime.datetime.strptime(
                              h.headers['last-modified'],
                              '%a, %d %b %Y %H:%M:%S %Z')
            if last_backup is not None:
                if last_modified < last_backup:
                    return
        else:
            return
        r = requests.get(url)
        while True:
            yield r
            if 'next' in r.links:
                r = requests.get(r.links['next']['url'])
            else:
                break
    
    def get_api(self, api_name, repo_name=None, last_backup=None):
        params = {'user': self.username, 'repo': repo_name}
        valid_apis = {
            'repos':
                'users/%(user)s/repos' % params,
            'open_pull_requests':
                'repos/%(user)s/%(repo)s/pulls' % params,
            'closed_pull_requests': 
                'repos/%(user)s/%(repo)s/pulls?state=closed' % params,
            'open_issues':
                'repos/%(user)s/%(repo)s/issues' % params,
            'closed_issues': 
                'repos/%(user)s/%(repo)s/issues?state=closed' % params
        }
        http_path = None
        if api_name in valid_apis:
            http_path = valid_apis[api_name]
        else:
            raise Exception('unknown API %s' % api_name)
              
        for r in self._api(http_path, last_backup):
            yield json.loads(r.text)

    def backup(self, api_name, repo_name):
        backup_dir = '%s/%s' % (self.backup_dir, repo_name)
        fname = '%s/%s.json' % (backup_dir, api_name)
        last_backup = self._last_backup(fname)
        data = self.get_api(api_name, repo_name, last_backup)
        if (self._write_backup(backup_dir, fname, data)):
            print 'Backed up: %s, %s' % (repo_name, api_name)

    def _last_backup(self, fname):
        if os.path.exists(fname):
            mtime = os.path.getmtime(fname)
            return datetime.datetime.fromtimestamp(mtime)
    
    def _write_backup(self, backup_dir, fname, data):
        (temphandle, tempfname) = tempfile.mkstemp()
        f = os.fdopen(temphandle, 'w')
        for datum in data:
            if datum:
                f.write(json.dumps(datum))
        f.close()
        if os.path.getsize(tempfname) > 0:
            try: 
                os.makedirs(backup_dir)
            except OSError as exc:
                if exc.errno == errno.EEXIST:
                    pass
                else:
                    raise
            os.rename(tempfname, fname)
            return True
        else:
            os.remove(tempfname)
            return False

def main():
    github = GitHub(username='mozilla')
    pages = github.get_api('repos')
    for repos in pages:
        for repo in repos:
            repo_name = repo['name']
            print 'Examining: %s' % repo_name
            
            for metadata in ['open_pull_requests', 'closed_pull_requests',
                             'open_issues', 'closed_issues']:
                github.backup(metadata, repo_name)

if __name__ == '__main__':
    main()
