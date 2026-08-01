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


class LegManager(TypedDict):
    managerId: str  # Ultra long hex string
    managerName: str
    secondManagerName: str
    secondManagerEmail: str
    SecondManagerPhone: str


class LegZone(TypedDict):
    zoneId: Optional[str]
    name: Optional[str]
    gemeindeName: Optional[str]
    unterwerk: Optional[str]
    uwName: Optional[str]
    uwGemeinde: Optional[str]


class LegStatus(TypedDict):
    statusId: str    # ANGELEGT, QUALIFIZIERT, ...
    statusDate: str  # YYYY-MM-DD


class LegHeader(TypedDict):
    legId: str                             # The long LEG ID used in other API calls
    descriptiveId: str                     # A shorter (numeric, leading zeros) ID
    description: str                       # User-defined name
    manager: LegManager
    zone: LegZone                          # Does not always appear to be populated
    gridLevel: str                         # Numeric grid level
    expectedActivationDate: Optional[str]  # YYYY-MM-DD
    expectedInactivationDate: Optional[str]
    expectedDissolutionDate: Optional[str]
    legStatus: List[LegStatus]


class LegHeaders(TypedDict):
    """Return schema for /leg-manager-dashboard/v1/leg-headers"""
    legHeaders: List[LegHeader]


class LegKpi(TypedDict):
    numberOfParticipants: int
    numberOfMeteringPoints: int
    sumModulePower: float
    sumConnectionPower: float
    minimumQuota: float
    reductionRateOfGridFees: float  # Percentage of net fee reduction, e.g. 40.0 for 40%
    qualified: bool


class LegMeteringPointSpecs(TypedDict):
    zoneId: str
    modulePower: float
    connectionPower: float
    trafostation: str
    gridLevel: str
    producer: bool
    smartMeter: bool
    validRateCategory: bool
    legId: str


class LegMeteringPointOrt(TypedDict):
    vstelle: str
    anlage: str
    anlageart: str
    locationStreet: str
    locationHousenumber: Optional[str]
    locationHousenumber2: Optional[str]
    locationPostal: Optional[str]
    locationCity: Optional[str]
    locationCountry: Optional[str]  # CH


class LegMeteringPoint(TypedDict):
    meteringPointId: str  # CH12345....
    businessPartnerId: str  # Ultra long hex string
    specifications: LegMeteringPointSpecs
    ort: LegMeteringPointOrt


class LegMeteringPointStatus(TypedDict):
    meteringPointId: str
    businessPartnerId: str
    legId: str
    participantStatus: str
    participantStatusDate: str
    progAktivierungsDatum: str
    progDeaktivierungsDatum: Optional[str]


class LegInvitation(TypedDict):
    invitationCode: str
    legId: str
    email: str
    createdAt: str
    expiredAt: Optional[str]
    revokedAt: Optional[str]
    redeemedAt: Optional[str]
    declinedAt: Optional[str]
    gpart: str  # Ultra long hex ID


class NamePerson(TypedDict):
    titleKey: str
    titleText: str
    firstNamePerson1: Optional[str]
    lastNamePerson1: Optional[str]
    firstNamePerson2: Optional[str]
    lastNamePerson2: Optional[str]
    birthdate: Optional[str]
    secondPerson: bool


class NameOrganization(TypedDict):
    name1: Optional[str]
    name2: Optional[str]
    name3: Optional[str]
    name4: Optional[str]


class Name(TypedDict):
    salutation: str
    type: str  # PERSON, ORGANISATION, ...
    namePerson: NamePerson
    nameOrga: NameOrganization
    nameGroup: dict


class CommunicationData(TypedDict):
    email: Optional[str]
    phone: Optional[str]
    fax: Optional[str]
    mobile: Optional[str]


class GpartData(TypedDict):
    gpart: str  # Ultra long hex ID
    name: Name
    type: str  # PERSON, ...
    communicationData: CommunicationData
    address: Optional[str]  # ???


class LegTimelimits(TypedDict):
    legActivationDate: str  # YYYY-MM-DD
    legDeactivationDate: str  # YYYY-MM-DD
    legDissolutionDate: str  # YYYY-MM-DD
    meteringPointActivationDate: str  # YYYY-MM-DD


class LegDetails(TypedDict):
    legId: str  # The long LEG ID
    kpi: LegKpi  # Some key numbers for the LEG
    basisInfo: LegHeader
    meteringPointList: List[LegMeteringPoint]
    meteringPointStatusList: List[LegMeteringPointStatus]
    managerMeteringPointList: List[LegMeteringPoint]  # ???
    managerMeteringPointStatusList: List[LegMeteringPointStatus]  # ???
    invitations: List[LegInvitation]
    gpartCommonData: List[GpartData]
    timeLimits: LegTimelimits


class LegDetailsResponse(TypedDict):
    """Return schema for /leg-manager-dashboard/v1/leg-details"""
    legDetails: LegDetails
