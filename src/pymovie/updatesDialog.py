"""Dialog that lists the PyMovie releases on GitHub, with their notes, and offers a download of any of them."""

import html
import sys

from PyQt5 import QtCore, QtGui, QtWidgets

from pymovie.checkForNewerVersion import getReleases, isNewerVersion, RELEASES_PAGE_URL, README_URL


class UpdatesDialog(QtWidgets.QDialog):
    def __init__(self, current_version, parent=None):
        super().__init__(parent)
        self.setWindowTitle('PyMovie releases')
        self.resize(900, 600)
        self.current_version = current_version

        QtWidgets.QApplication.setOverrideCursor(QtCore.Qt.WaitCursor)
        try:
            self.releases, error = getReleases()
        finally:
            QtWidgets.QApplication.restoreOverrideCursor()

        layout = QtWidgets.QVBoxLayout(self)
        summary = QtWidgets.QLabel(self)
        summary.setWordWrap(True)
        layout.addWidget(summary)

        if sys.platform == 'win32':
            how = ('To change version: select a release, click the <b>Download</b> button, close PyMovie, then '
                   'replace your PyMovie.exe with the downloaded one. The first start of a different version '
                   'takes a little longer while it unpacks.')
        else:
            how = f'MacOS / Linux: follow the instructions in the <a href="{README_URL}">README</a> to update.'
        howLabel = QtWidgets.QLabel(how, self)
        howLabel.setWordWrap(True)
        howLabel.setOpenExternalLinks(True)
        layout.addWidget(howLabel)

        splitter = QtWidgets.QSplitter(QtCore.Qt.Horizontal, self)
        layout.addWidget(splitter, stretch=1)
        self.releaseList = QtWidgets.QListWidget(splitter)
        self.notes = QtWidgets.QTextBrowser(splitter)
        self.notes.setOpenExternalLinks(True)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 4)
        splitter.setSizes([300, 600])

        buttons = QtWidgets.QHBoxLayout()
        layout.addLayout(buttons)
        self.downloadButton = QtWidgets.QPushButton('Download', self)
        pageButton = QtWidgets.QPushButton('Open releases page', self)
        closeButton = QtWidgets.QPushButton('Close', self)
        buttons.addWidget(self.downloadButton)
        buttons.addWidget(pageButton)
        buttons.addStretch()
        buttons.addWidget(closeButton)
        self.downloadButton.setEnabled(False)
        self.downloadButton.clicked.connect(self.downloadSelected)
        pageButton.clicked.connect(lambda: self.openUrl(RELEASES_PAGE_URL))
        closeButton.clicked.connect(self.accept)

        if self.releases is None:
            summary.setText(f'The list of releases could not be fetched: {error}')
            self.notes.setHtml(f'<p>The releases can be seen at '
                               f'<a href="{RELEASES_PAGE_URL}">{RELEASES_PAGE_URL}</a></p>')
            return
        if not self.releases:
            summary.setText('No releases were found on GitHub.')
            return

        newer = [r for r in self.releases if isNewerVersion(r['version'], current_version)]
        if newer:
            summary.setText(f'<b>You are running PyMovie {current_version}. {len(newer)} newer '
                            f'release{"s are" if len(newer) > 1 else " is"} available; the latest is '
                            f'{newer[0]["version"]}.</b>')
        else:
            summary.setText(f'You are running PyMovie {current_version}, the most recent release. '
                            f'Older releases are listed too, in case you want one of them.')

        for rel in self.releases:
            label = f'{rel["version"]}  {rel["date"]}'
            if rel['version'] == current_version:
                label += '  (running)'
            elif rel in newer:
                label += '  (new)'
            item = QtWidgets.QListWidgetItem(label)
            if rel in newer:
                font = item.font()
                font.setBold(True)
                item.setFont(font)
            self.releaseList.addItem(item)
        self.releaseList.currentRowChanged.connect(self.showRelease)
        self.releaseList.setCurrentRow(0)

    def showRelease(self, row):
        if row < 0:
            return
        rel = self.releases[row]
        self.notes.setHtml(f'<h3>{html.escape(rel["name"])} &nbsp;<small>({html.escape(rel["date"])})</small></h3>'
                           f'<div style="white-space: pre-wrap;">{html.escape(rel["notes"])}</div>'
                           f'<p><a href="{html.escape(rel["page_url"])}">release page</a></p>')
        if rel['exe_url']:
            self.downloadButton.setEnabled(True)
            self.downloadButton.setText(f'Download PyMovie.exe {rel["version"]}')
        else:
            self.downloadButton.setEnabled(False)
            self.downloadButton.setText(f'{rel["version"]} has no PyMovie.exe')

    def downloadSelected(self):
        row = self.releaseList.currentRow()
        if row >= 0 and self.releases[row]['exe_url']:
            self.openUrl(self.releases[row]['exe_url'])

    @staticmethod
    def openUrl(url):
        # The browser does the download (into the user's usual Downloads folder)
        QtGui.QDesktopServices.openUrl(QtCore.QUrl(url))
