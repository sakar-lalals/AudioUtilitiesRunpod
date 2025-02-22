class AWSAccessKeyNotExistsException(Exception):
    def __init__(self, message:str = ''):
        super().__init__(message)
        self.message = message

class AWSSecretKeyNotExistsException(Exception):
    def __init__(self, message:str = ''):
        super().__init__(message)
        self.message = message

class VoiceModelNotFoundException(Exception):
    def __init__(self, message:str = ''):
        super().__init__(message)
        self.message = message

class OutputNameConfigNotFoundException(Exception):
    def __init__(self, message:str = ''):
        super().__init__(message)
        self.message = message
