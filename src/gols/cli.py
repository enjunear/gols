"""
Module that contains the command line app.

Why does this file exist, and why not put this in __main__?

  You might be tempted to import things from __main__ later, but that will cause
  problems: the code will get executed twice:

  - When you run `python -mgols` python will execute
    ``__main__.py`` as a script. That means there won't be any
    ``gols.__main__`` in ``sys.modules``.
  - When you import __main__ it will get executed again (as a module) because
    there's no ``gols.__main__`` in ``sys.modules``.

  Also see (1) from http://click.pocoo.org/5/setuptools/#setuptools-integration
"""

import logging
import os
import shutil

import click
import requests

logger = logging.getLogger(__name__)
logging.basicConfig()


@click.group()
@click.option('--debug/--no_debug', default=False,
              help='Set to true to see debug logs on top of info')
def main(debug):
    if debug:
        requests_log = logging.getLogger("requests.packages.urllib3")
        requests_log.setLevel(logging.DEBUG)
        requests_log.propagate = True
        logging.root.setLevel(level=logging.DEBUG)
        logger.info('Debug level set on')
    else:
        logger.setLevel(level=logging.INFO)
        logger.info('Info level set on')


@main.command(short_help='uploads .fit files to your garmin connect account')
@click.option('--directory_fit', '-d', required=True,
              type=click.Path(exists=True, file_okay=False),
              help='Path of your .fit files on your watch mount path')
@click.option('--move', '-m', required=False,
              type=click.Path(exists=True, file_okay=False, dir_okay=True, writable=True, readable=True),
              help='Directory to move .fit files to upon upload')
@click.option('--username', '-u', required=True,
              default=lambda: os.environ.get('GARMINCONNECT_USERNAME', ''),
              help='The GARMINCONNECT_USERNAME environment variable should you have one set')  # noqa
@click.option('--password', '-p', required=True,
              default=lambda: os.environ.get('GARMINCONNECT_PASSWORD', ''),
              help='The GARMINCONNECT_PASSWORD environment variable should you have one set ')  # noqa
@click.option('--conf_dir_fit', '-c', required=True,
               type=click.Path(exists=True, file_okay=False, dir_okay=True, writable=True, readable=True))  # noqa
def upload(directory_fit, move, username, password, conf_dir_fit):
    logger.info('Uplading stuff')
    headers = {
        'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:51.0) Gecko/20100101 Firefox/51.0',
    }
    params_login = {
        'service': 'https://connect.garmin.com/modern/',
        'webhost': 'olaxpw-conctmodern011',
        'source': 'https://connect.garmin.com/en-US/signin',
        'redirectAfterAccountLoginUrl': 'https://connect.garmin.com/modern/',
        'redirectAfterAccountCreationUrl': 'https://connect.garmin.com/modern/',
        'gauthHost': 'https://sso.garmin.com/sso',
        'locale': 'en_US',
        'id': 'gauth-widget',
        'cssUrl': 'https://static.garmincdn.com/com.garmin.connect/ui/css/gauth-custom-v1.2-min.css',
        'clientId': 'GarminConnect',
        'rememberMeShown': 'true',
        'rememberMeChecked': 'false',
        'createAccountShown': 'true',
        'openCreateAccount': 'false',
        'usernameShown': 'false',
        'displayNameShown': 'true',
        'consumeServiceTicket': 'false',
        'initialFocus': 'true',
        'embedWidget': 'false',
        'generateExtraServiceTicket': 'false',
        'globalOptInShown': 'false',
        'globalOptInChecked': 'false',
        'connectLegalTerms': 'true',
    }
    data_login = {
        'username': username,
        'password': password,
        'embed': 'true',
        'lt': 'e1s1',
        '_eventId': 'submit',
        'displayNameRequired': 'false',
        'rememberme': 'on',
    }

    # begin session with headers because, requests client isn't an option, dunno if Icewasel is still banned...
    logger.info('Login into Garmin connect')
    s = requests.session()
    s.headers.update(headers)
    # we need the cookies from the login page before we can post the user/pass
    url_login = 'https://sso.garmin.com/sso/login'
    req_login = s.get(url_login, params=params_login)
    if req_login.status_code != 200:
        logger.info('issue with {}, you can turn on debug for more info'.format(
            req_login))
    req_login2 = s.post(url_login, data=data_login)
    if req_login2.status_code != 200:
        logger.info('issue with {}, you can turn on debug for more info'.format(
            req_login2))
    # we need that to authenticate further, kind like a weird way to login but...
    t = req_login2.cookies.get('CASTGC')
    t = 'ST-0' + t[4:]
    # now the auth with the cookies we got
    # url_post_auth = 'https://connect.garmin.com/modern' this one I still don't know how to get it
    url_post_auth = 'https://connect.garmin.com/post-auth/login'
    params_post_auth = {'ticket': t}
    req_post_auth = s.get(url_post_auth, params=params_post_auth)
    if req_post_auth.status_code != 200:
        logger.info('issue with {}, you can turn on debug for more info'.format(
            req_post_auth))
    logger.info('Let\'s upload stuff now')
    # login should be done we upload now

    # url_upload = 'https://connect.garmin.com/proxy/upload-service-1.1/json/upload/.fit'
    url_upload = 'https://connect.garmin.com/modern/proxy/upload-service/upload/.fit'
    if len(os.listdir(directory_fit)):
        logger.debug([f for f in os.listdir(directory_fit) if os.path.isfile(os.path.join(directory_fit, f))])
        for filename in [f for f in os.listdir(directory_fit) if os.path.isfile(os.path.join(directory_fit, f))]:
            logger.info('uploading:  {}'.format(filename))
            files = {'data': (filename,
                              open(os.path.join(directory_fit, filename), 'rb'),
                              'application/octet-stream')
                     }
            s.headers.update({'Referer': 'https://connect.garmin.com/modern/import-data', 'NK': 'NT'})
            req5 = s.post(url_upload, files=files)
            if req5.status_code != 200:
                logger.info(
                    'issue with {}, you can turn on debug for more info'.format(
                        req5))

            # fn = req5.json()['detailedImportResult']['fileName']
            if 'failures' in req5.json()['detailedImportResult']:
                for failure in req5.json()['detailedImportResult']['failures']:
                    m_failures = failure['messages'][0]['content']
                    logger.info(m_failures)
            if 'successes' in req5.json()['detailedImportResult']:
                for successes in req5.json()['detailedImportResult']['successes']:
                    m_success = 'https://connect.garmin.com/modern/activity/' + str(
                        successes['internalId'])
                    logger.info(m_success)

            if os.path.isdir(move):
                shutil.move(os.path.join(directory_fit, filename),
                            os.path.join(move, filename))

        logger.info('Done uploading')
    else:
        logger.info('No file found in {}'.format(directory_fit))
    logger.info('Finished')
