# -*- encoding: utf-8 -*-
# vim: ts=4 sw=4 expandtab ai

"""
Usage:
    hammer sc_param [OPTIONS] SUBCOMMAND [ARG] ...

Parameters:
    SUBCOMMAND                    subcommand
    [ARG] ...                     subcommand arguments

Subcommands:
    info                          Show a smart class parameter.
    list                          List all smart class parameters
    update                        Update a smart class parameter.
"""

from robottelo.cli.base import Base


class SmartClassParameter(Base):
    """
    Manipulates smart class parameters in Foreman
    """

    def __init__(self):
        """
        Sets the base command for class.
        """
        Base.__init__(self)
        self.command_base = "sc_param"
