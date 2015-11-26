# -*- encoding: utf-8 -*-
"""Test class for SSO (CLI)"""

from robottelo.decorators import stubbed
from robottelo.test import CLITestCase


class TestSSOCLI(CLITestCase):
    """Test Class for SSO CLI"""

    # Notes for SSO testing:
    # Of interest... In some testcases I've placed a few comments prefaced with
    # "devnote:" These are -- obviously -- notes from developers that might
    # help reiterate something important or a reminder of way(s) to test
    # something.

    # There may well be more cases that I have missed for this feature, and
    # possibly other LDAP types. These (in particular, the LDAP variations)
    # can be easily added later.

    @stubbed()
    def test_sso_kerberos_cli(self):
        """@test: kerberos user can login to CLI

        @feature: SSO

        @setup: kerberos configured against foreman.

        @assert: Log in to hammer cli successfully

        @status: Manual
        """

    @stubbed()
    def test_sso_ipa_cli(self):
        """@test: IPA user can login to CLI

        @feature: SSO

        @setup: IPA configured against foreman.

        @assert: Log in to hammer cli successfully

        @status: Manual
        """

    @stubbed()
    def test_sso_openldap_cli(self):
        """@test: OpenLDAP user can login to CLI

        @feature: SSO

        @setup: OpenLDAP configured against foreman.

        @assert: Log in to hammer cli successfully

        @status: Manual
        """
