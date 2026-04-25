import uuid
from src.models.customer import Customer
from src.models.vehicle import Vehicle


def test_customer_columns():
    shop_id = uuid.uuid4()
    c = Customer(shop_id=shop_id, name="Mike Rodriguez", email="mike@example.com", phone="+15551234567")
    assert c.shop_id == shop_id
    assert c.name == "Mike Rodriguez"
    assert c.email == "mike@example.com"
    assert c.phone == "+15551234567"


def test_customer_auto_id():
    c = Customer(shop_id=uuid.uuid4(), name="Auto ID Test")
    assert c.id is not None


def test_vehicle_columns():
    customer_id = uuid.uuid4()
    v = Vehicle(
        customer_id=customer_id,
        year=2021,
        make="Honda",
        model="Civic",
        trim="LX",
        vin="1HGBH41JXMN109186",
        color="Silver",
    )
    assert v.customer_id == customer_id
    assert v.year == 2021
    assert v.make == "Honda"
    assert v.model == "Civic"
    assert v.trim == "LX"
    assert v.vin == "1HGBH41JXMN109186"
    assert v.color == "Silver"


def test_vehicle_auto_id():
    v = Vehicle(customer_id=uuid.uuid4(), year=2019, make="Ford", model="F-150")
    assert v.id is not None


def test_vehicle_optional_fields_default_none():
    v = Vehicle(customer_id=uuid.uuid4(), year=2020, make="BMW", model="3 Series")
    assert v.trim is None
    assert v.vin is None
    assert v.color is None
