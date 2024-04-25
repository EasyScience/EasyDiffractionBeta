import os
import pathlib

# Help functions

def change_cwd_to_tests():
    """Changes the current directory to the directory of this script file."""
    os.chdir(os.path.dirname(__file__))

def desired_img_path(fname:str):
    return os.path.join('screenshots', 'desired', fname)

def actual_img_path(fname:str):
    return os.path.join('screenshots', 'actual', fname)

# Set up paths

change_cwd_to_tests()

# Tests

def test__HomePage(image_diff):
    fname = 'HomePage.png'
    desired = desired_img_path(fname)
    actual = actual_img_path(fname)
    assert image_diff(desired, actual)

def test__ProjectPage(image_diff):
    fname = 'ProjectPage.png'
    desired = desired_img_path(fname)
    actual = actual_img_path(fname)
    assert image_diff(desired, actual)

def test__ModelPage(image_diff):
    fname = 'ModelPage.png'
    desired = desired_img_path(fname)
    actual = actual_img_path(fname)
    assert image_diff(desired, actual)

def test__ExperimentPage(image_diff):
    fname = 'ExperimentPage.png'
    desired = desired_img_path(fname)
    actual = actual_img_path(fname)
    assert image_diff(desired, actual)

def test__AnalysisPage(image_diff):
    fname = 'AnalysisPage.png'
    desired = desired_img_path(fname)
    actual = actual_img_path(fname)
    assert image_diff(desired, actual)

def test__SummaryPage(image_diff):
    fname = 'SummaryPage.png'
    desired = desired_img_path(fname)
    actual = actual_img_path(fname)
    assert image_diff(desired, actual)

# Debug

if __name__ == '__main__':
    pass
