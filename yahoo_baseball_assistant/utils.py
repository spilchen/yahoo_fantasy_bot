import unicodedata


def normalized(name):
    """Normalize a name to remove any accents

    :param name: Input name to normalize
    :type name: str
    :return: Normalized name
    :rtype: str
    """
    return unicodedata.normalize('NFD', name).encode(
        'ascii', 'ignore').decode('utf-8')
