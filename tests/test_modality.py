from regextractor.metadata import classify_obligation


def test_shall_not_not_reduced_to_shall():
    assert classify_obligation("A bank shall not refuse payment.") == "Prohibitory"
    assert classify_obligation("A bank shall issue a draft.") == "Mandatory"


def test_must_not_and_may_not():
    assert classify_obligation("Staff must not accept the instrument.") == "Prohibitory"
    assert classify_obligation("The bank may not disclose the data.") == "Prohibitory"


def test_may_vs_must():
    assert classify_obligation("The bank may call for succession certificates.") == "Discretionary"
    assert classify_obligation("The bank must display the procedure.") == "Mandatory"


def test_informational_definition():
    assert classify_obligation("Customer means a user of bank services.") == "Informational"
