import pytest
result=pytest.main(['/opt/argus/tests','-q','-p','no:cacheprovider'])
if result:
    raise RuntimeError('Embedded Python tests failed')
print('ARGUS_EMBEDDED_TESTS_OK')
