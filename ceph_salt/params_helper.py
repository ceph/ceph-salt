class Validator():
    @classmethod
    def validate(cls, value):
        raise NotImplementedError()


class Transformer():
    @classmethod
    def transform(cls, value):
        raise NotImplementedError()


class BooleanStringValidator(Validator):
    """Validate a string is in boolean type."""
    @classmethod
    def validate(cls, value):
        return value.lower() in ['true', 'false', '1', '0']


class BooleanStringTransformer(Transformer):
    """Transform a boolean string to boolean type."""
    @classmethod
    def transform(cls, value):
        return value.lower() in ['true', '1']
