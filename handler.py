import json
import uuid
from urllib2 import urlopen
from urlparse import urljoin

import boto3

import logging
log = logging.getLogger()

URL = 'https://mandrillapp.com/api/1.0/'

dynamodb = boto3.resource('dynamodb')

Config = dynamodb.Table('Config')


def send_email(event, context):
    uid = event['pathParameters']['uuid']
    try:
        uid = uuid.UUID(uid)
    except ValueError:
        log.info('Invalid UUID: %r', uid)
        return {'statusCode': 404, 'body': ''}

    # Try to retrieve config
    resp = Config.get_item(Key={'uuid': str(uid)})
    config = resp.get('Item')

    if not config:
        return {'statusCode': 400, 'body': ''}

    try:
        data = json.loads(event['body'])
    except json.JSONDecodeError as e:
        log.info('Invalid Body: %r', e)
        return {'statusCode': 400, 'body': 'Invalid JSON format'}

    # XXX Generate content
    req = {
        'key': config['key'],
        'template_name': config['template'],
        'template_content': [],
        'message': {
            'to': [
                {'email': data['target-email'], 'type': 'to'}
            ],
            'merge': True,
            'merge_langauge': 'handlebars',
            'global_merge_vars': [
                {'name': key, 'content': value}
                for key, value in data.items()
            ],
        },
    }

    # Post to Mandrill
    resp = urlopen(urljoin(URL, 'messages/send-template.json'), data=json.dumps(req))
    if resp.getcode() != 200:
        body = resp.read()
        log.error('Error from Mandrill: [%r] %r', resp.getcode(), body)
        return {'statusCode': 400, 'body': 'Service Error'}

    content = json.loads(resp.read())
    if isinstance(content, dict):
        log.warn('Rejected by Mandrill: %r', content)
        return {'statusCode': 400, 'body': content}

    return {'statusCode': 204, 'body': '', 'headers': {"Access-Control-Allow-Origin" : "*"}}
