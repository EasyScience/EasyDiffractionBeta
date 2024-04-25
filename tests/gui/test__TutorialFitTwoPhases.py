import os

# Help functions

def desired_img_path(fname:str):
    return os.path.join('screenshots', 'desired', fname)

def actual_img_path(fname:str):
    return os.path.join('screenshots', 'actual', fname)

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
