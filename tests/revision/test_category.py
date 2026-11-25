"""The document category follows the file name, not the outline model."""

from verifiable_tutor.revision.category import document_category


def test_categories_follow_the_file_name():
    assert document_category("Assignment_1_final") == "assignment"
    assert document_category("ACS_Lecture_3_2026F") == "lecture"
    assert document_category("Tutorial_6") == "tutorial"
    assert document_category("TACC_Toturial") == "tutorial"
    assert document_category("course_project") == "other"
