# -*- coding: utf-8 -*-
import mock
import pytest
from pyramid import httpexceptions
from pyramid import testing

from h import accounts

# The fixtures required to mock all of get_user()'s dependencies.
get_user_fixtures = pytest.mark.usefixtures('util', 'get_by_username')


@get_user_fixtures
def test_get_user_calls_split_user(util):
    """It should call split_user() once with the given userid."""
    util.user.split_user.return_value = {
        'username': 'fred', 'domain': 'hypothes.is'}

    accounts.get_user('acct:fred@hypothes.is', mock.Mock())

    util.user.split_user.assert_called_once_with('acct:fred@hypothes.is')


@get_user_fixtures
def test_get_user_returns_None_if_split_user_raises_ValueError(util):
    util.user.split_user.side_effect = ValueError

    assert accounts.get_user('userid', mock.Mock()) is None


@get_user_fixtures
def test_get_user_returns_None_if_domain_does_not_match(util):
    request = mock.Mock(auth_domain='hypothes.is')
    util.user.split_user.return_value = {
        'username': 'username', 'domain': 'other'}

    assert accounts.get_user('userid', request) is None


@get_user_fixtures
def test_get_user_calls_get_by_username(util, get_by_username):
    """It should call get_by_username() once with the username."""
    request = mock.Mock(auth_domain='hypothes.is')
    util.user.split_user.return_value = {
        'username': 'username', 'domain': 'hypothes.is'}

    accounts.get_user('acct:username@hypothes.is', request)

    get_by_username.assert_called_once_with('username')


@get_user_fixtures
def test_get_user_returns_user(util, get_by_username):
    """It should return the result from get_by_username()."""
    request = mock.Mock(auth_domain='hypothes.is')
    util.user.split_user.return_value = {
        'username': 'username', 'domain': 'hypothes.is'}

    assert accounts.get_user('acct:username@hypothes.is', request) == (
        get_by_username.return_value)


authenticated_user_fixtures = pytest.mark.usefixtures('get_user')


@authenticated_user_fixtures
def test_authenticated_user_calls_get_user(config, get_user):
    """It should call get_user() correctly."""
    request = testing.DummyRequest()
    config.testing_securitypolicy('userid')

    accounts.authenticated_user(request)

    get_user.assert_called_once_with('userid', request)


@authenticated_user_fixtures
def test_authenticated_user_invalidates_session_if_user_does_not_exist(config, get_user):
    """It should log the user out if they no longer exist in the db."""
    request = testing.DummyRequest()
    request.current_route_url = lambda: '/'
    request.session.invalidate = mock.Mock()
    config.testing_securitypolicy('userid')
    get_user.return_value = None

    try:
        accounts.authenticated_user(request)
    except Exception:
        pass

    request.session.invalidate.assert_called_once_with()


@authenticated_user_fixtures
def test_authenticated_user_does_not_invalidate_session_if_not_authenticated(config, get_user):
    """
    If authenticated_userid is None it shouldn't invalidate the session.

    Even though the user with id None obviously won't exist in the db.

    This also tests that it doesn't raise a redirect in this case.

    """
    request = testing.DummyRequest()
    request.current_route_url = lambda: '/'
    request.session.invalidate = mock.Mock()
    config.testing_securitypolicy()
    get_user.return_value = None

    accounts.authenticated_user(request)

    assert not request.session.invalidate.called


@authenticated_user_fixtures
def test_authenticated_user_redirects_if_user_does_not_exist(config, get_user):
    request = testing.DummyRequest()
    request.current_route_url = lambda: '/the/page/that/I/was/on'
    config.testing_securitypolicy('userid')
    get_user.return_value = None

    with pytest.raises(httpexceptions.HTTPFound) as exc:
        accounts.authenticated_user(request)

    assert exc.value.location == '/the/page/that/I/was/on', (
        'It should redirect to the same page that was requested')


@authenticated_user_fixtures
def test_authenticated_user_returns_user_from_get_user(get_user):
    """It should return the user from get_user()."""
    request = mock.Mock(authenticated_userid='userid')

    assert accounts.authenticated_user(request) == get_user.return_value


@pytest.fixture
def util(patch):
    return patch('h.accounts.util')


@pytest.fixture
def get_by_username(patch):
    return patch('h.accounts.models.User.get_by_username', autospec=False)


@pytest.fixture
def get_user(patch):
    return patch('h.accounts.get_user')
