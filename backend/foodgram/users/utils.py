import re

from rest_framework import serializers


def username_validator(value):
    if not re.match(r'^[\w.@+-]+$', value):
        raise serializers.ValidationError(
            '''Username can only contain letters,
            numbers and signs @/./+/-/_'''
        )
    if value.lower() == 'me':
        raise serializers.ValidationError(
            'Username "me" is not allowed.'
        )
    return value
