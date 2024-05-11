from typing import TypedDict, List, Optional


class Address(TypedDict):
    addressNumber: str
    street: str
    houseNumber: str
    houseNumberDetails: str
    locationDetails: str
    floor: str
    postalCode: str
    city: str


class ISDContract(TypedDict):
    """Used for the contracts property in InstallationSelectionData."""
    gpart: str
    vkonto: str
    vertrag: str
    anlage: str
    vstelle: str
    haus: str
    einzdat: str
    auszdat: Optional[str]
    sparte: str


class ISDAnlage(TypedDict):
    """Used for the eanl property in InstallationSelectionData."""
    anlage: str
    sparte: str
    vstelle: str
    anlart: str
    spebene: str
    zzenergietraeger: Optional[str]
    zzevgstat: Optional[str]
    zzevganlage: Optional[str]
    eanlhTariftyp: str
    eanlhAbleinh: str


class ISDStelle(TypedDict):
    vstelle: str
    haus: str
    eigent: str
    vbsart: str
    lgzusatz: str
    floor: str
    zzlage: str
    zzlgzusatz: str
    iflotZzanobjart: str
    iflotZzeigen: str
    iflotZzegid: str
    address: Address


class ISDFkkVkp(TypedDict):
    vkont: str
    gpart: str
    opbuk: str
    stdbk: str
    abrwe: Optional[str]
    abwra: Optional[str]
    abwma: Optional[str]
    ebvty: Optional[str]
    abvty: str
    ezawe: str
    azawe: str
    vkpbz: str
    ktokl: str
    consolidatorId: str
    zzRechDet: str


class InstallationSelectionData(TypedDict):
    """Return schema for /consumption-view/v1/installation-selection-data?installationVariant=CONSUMPTION"""
    contracts: List[ISDContract]
    eanl: List[ISDAnlage]
    evbs: List[ISDStelle]
    fkkvkp: List[ISDFkkVkp]
    commonData: Optional[str]


class IDProperty(TypedDict):
    property: str
    ab: str
    bis: str


class InstallationData(TypedDict):
    """Return schema for /consumption-view/v1/installation-data?installationId=..."""
    status: List[IDProperty]


class Value(TypedDict):
    value: float
    timestamp: int
    date: str
    time: str
    status: str


class Series(TypedDict):
    level: str
    energyType: Optional[str]
    sourceType: Optional[str]
    tariffType: str
    ab: str
    bis: str
    values: List[Value]


class ConsumptionData(TypedDict):
    """Return schema for /consumption-view/v1/consumption-data?installationId=..."""
    series: Optional[Series]
    seriesHt: Optional[Series]
    seriesNetz: Optional[Series]
    seriesNetzHt: Optional[Series]
    seriesNetzHt: Optional[Series]
    seriesNt: Optional[Series]
