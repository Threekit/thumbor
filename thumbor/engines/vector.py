#!/usr/bin/python
# -*- coding: utf-8 -*-

# thumbor imaging service
# https://github.com/thumbor/thumbor/wiki

# Licensed under the MIT license:
# http://www.opensource.org/licenses/mit-license
# Copyright (c) 2011 globo.com thumbor@googlegroups.com

from __future__ import absolute_import

import re
from subprocess import Popen, PIPE
from thumbor.engines.pil import Engine as PILEngine
from thumbor.utils import EXTENSION, logger
import os
from tempfile import mkstemp

INKSCAPE_SIZE_RE = re.compile(r'(-?[\d\.]+)')

class Engine(PILEngine):
    @property
    def size(self):
        return self.image_size

    def inkscape_toSvg(self):
        if not self.dirty: return
        if not self.buffer: return
        self.dirty = False

        mimeType = self.get_mimetype(self.buffer)
        file_ext = EXTENSION.get(mimeType, self.extension)
        if(file_ext == '.svg'): return

        # write buffer to tmp file. `inkscape --pipe` doesn't work with stdin because inkscape needs the file ext, otherwise it assumes the input is an svg

        tmp_fd, tmp_file_path = mkstemp(file_ext)

        try:
            f = os.fdopen(tmp_fd, "w")
            f.write(self.buffer)
            f.close()

            command = [
                self.context.server.inkscape_path,
                tmp_file_path,
                '--export-plain-svg=-'
            ]

            # execute inkscape on tmp file

            p_inkscape = Popen(
                command,
                stdout=PIPE,
                stderr=PIPE
            )
            stdout_data, stderr_data = p_inkscape.communicate(input=self.buffer)
            # logger.warn(stderr_data)
            # Note, stderr_data is full of "CRITICAL" inkscape warnings that don't mean much, so we can ignore them
            # Most of them are caused by not running `dbus-run-session inkscape` instead of `inkscape`
            # The returncode does seem to be reliable, and we can further validate by calling get_mimetype on the result
            
            if p_inkscape.returncode != 0 or not stdout_data or self.get_mimetype(stdout_data) != 'image/svg+xml':
                errorMsg = 'Issue executing inkscape command. Inkscape command returned errorlevel {0} for command "{1}"'.format(p_inkscape.returncode, ' '.join(command));
                logger.error(errorMsg)
                self.image = None
                return

            self.buffer = stdout_data

        finally:
            os.remove(tmp_file_path)

    def is_multiple(self):
        return False

    def update_image_info(self):
        self.image_size = [100, 100]

        self.inkscape_toSvg()
        if self.get_mimetype(self.buffer) != 'image/svg': return
        p = Popen([self.context.server.inkscape_path, '--pipe', '--query-width', '--query-height'], stdout=PIPE, stdin=PIPE, stderr=PIPE)
        stdout_data, stderr_data = p.communicate(input=self.buffer)
        width, height = INKSCAPE_SIZE_RE.findall(stdout_data)
        self.image_size = [float(width), float(height)]

    def load(self, buffer, extension):
        self.extension = extension
        self.buffer = buffer
        self.image = ''

        self.dirty = True
        self.update_image_info()

    def extract_cover(self):
        self.update_image_info()

    def read(self, extension=None, quality=None):
        return self.buffer

    def draw_rectangle(self, x, y, width, height):
        raise NotImplementedError()

    def resize(self, width, height):
        raise NotImplementedError()

    def crop(self, left, top, right, bottom):
        raise NotImplementedError()

    def rotate(self, degrees):
        raise NotImplementedError()

    def flip_vertically(self):
        raise NotImplementedError()

    def flip_horizontally(self):
        raise NotImplementedError()

    def convert_to_grayscale(self, update_image=True, with_alpha=True):
        raise NotImplementedError()

    def reorientate(self, override_exif=True):
        pass
