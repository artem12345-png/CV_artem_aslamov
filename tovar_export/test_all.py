from worker_tovar_export import parse_property


def test_Q1():
    assert parse_property(None, "") == ''


def test_Q2():
    assert parse_property(' ', 'test.test') == ''
