from zipfile import ZipFile

import pytest

from odemagg.utils import unzip_files


@pytest.fixture
def test_zip_file(tmp_path):
    """Creates a test zip file containing a mix of file types"""
    zip_path = tmp_path / "test.zip"
    with ZipFile(zip_path, "w") as zip_file:
        zip_file.writestr("image.tif", "tif")
        zip_file.writestr("image.tiff", "tiff")
        zip_file.writestr("image.tif.png", "tif.png")
    return zip_path


def test_unzip_files_all(test_zip_file, tmp_path):
    target_dir = tmp_path / "output"
    extracted = unzip_files(test_zip_file, target_dir)
    assert len(extracted) == 3
    assert all(i.exists() for i in extracted)


def test_unzip_files_specific(test_zip_file, tmp_path):
    target_dir = tmp_path / "output"
    file_types = [".tif", ".tiff"]
    extracted = unzip_files(test_zip_file, target_dir, file_types=file_types)
    assert len(extracted) == 2
    assert all(i.exists() for i in extracted)
    assert all(i.name in ["image.tif", "image.tiff"] for i in extracted)


def test_unzip_files_no_matching(test_zip_file, tmp_path):
    target_dir = tmp_path / "output"
    file_types = [".abc"]
    with pytest.warns(UserWarning):
        extracted = unzip_files(test_zip_file, target_dir, file_types=file_types)
        assert extracted == []
