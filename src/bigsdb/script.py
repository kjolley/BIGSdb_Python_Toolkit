# Written by Keith Jolley
# Copyright (c) 2024, University of Oxford
# E-mail: keith.jolley@biology.ox.ac.uk
#
# This file is part of BIGSdb Python Toolkit.
#
# BIGSdb Python Toolkit is free software: you can redistribute it and/or
# modify it under the terms of the GNU General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# BIGSdb Python Toolkit is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with BIGSdb Python Toolkit. If not,
# see <https://www.gnu.org/licenses/>.

import logging
from bigsdb.base_application import BaseApplication
from bigsdb.constants import DIRS


class Script(BaseApplication):
    def __init__(
        self,
        database=None,
        config_dir=DIRS["CONFIG_DIR"],
        dbase_config_dir=DIRS["DBASE_CONFIG_DIR"],
        host=None,
        port=None,
        user=None,
        password=None,
        logger=None,
        testing=False,
    ):
        self._init_logger(logger=logger)

        super(Script, self).__init__(
            database=database,
            config_dir=config_dir,
            dbase_config_dir=dbase_config_dir,
            host=host,
            port=port,
            user=user,
            password=password,
            logger=self.logger,
        )

    def _init_logger(self, logger=None):
        if logger:
            self.logger = logger
            return
        self.logger = logging.getLogger(__name__)
        log_file = "/var/log/bigsdb_scripts.log"

        # Create handlers
        c_handler = logging.StreamHandler()
        f_handler = logging.FileHandler(log_file)
        c_handler.setLevel(logging.WARNING)
        f_handler.setLevel(logging.ERROR)

        # Create formatters and add it to handlers
        c_format = logging.Formatter(
            "%(levelname)s - %(module)s:%(lineno)d - %(message)s"
        )
        f_format = logging.Formatter(
            "%(asctime)s - %(levelname)s: - %(module)s:%(lineno)d - %(message)s"
        )
        c_handler.setFormatter(c_format)
        f_handler.setFormatter(f_format)

        # Add handlers to the logger
        self.logger.addHandler(c_handler)
        self.logger.addHandler(f_handler)
