import ipaddress
import logging
from privacyidea.lib.error import ParameterError
from privacyidea.lib.resolver import get_resolver_object
from privacyidea.lib.resolvers.LDAPIdResolver import IdResolver
from privacyidea.lib.config import get_from_config,set_privacyidea_config
from re import match

DEFAULT_USER_RISK = 3
DEFAULT_IP_RISK = 1
DEFAULT_SERVICE_RISK = 5

LDAP_USER_GROUP_DN_STR = "ldap_user_group_base_dn"
LDAP_USER_GROUP_SEARCH_ATTR_STR = "ldap_user_group_search_attr"
LDAP_GROUP_RESOLVER_NAME_STR = "resolver_name"

CONFIG_GROUPS_RISK_SCORES_KEY = "user_groups_risk_scores"
CONFIG_SERVICES_RISK_SCORES_KEY = "services_risk_scores"
CONFIG_IP_RISK_SCORES_KEY = "ip_risk_scores"


log = logging.getLogger(__name__) 

def calculate_risk(ip: str,service: str,user_groups: list):
    """Calculates the risk score based on the IP, service and user group.
    If the value of the parameter does not have a defined risk score, the default risk score is used instead.

    Args:
        ip (str): the IP
        service (str): the service name
        user_groups (list): the list of groups the user belongs to

    Returns:
        float: the risk score
    """
    ip_risk_score = get_ip_risk_score(ip)
    service_risk_score = get_service_risk_score(service)
    user_risk_score = get_user_risk_score(user_groups)

    return user_risk_score + service_risk_score + ip_risk_score    

def get_groups():
    """Retrieves all groups using the group configuration

    Returns:
        list: the groups retrieved
    """
    resolver = _get_group_resolver()
    if not resolver:
        return []
    
    _groups = resolver.getUserList({})
    groups = set()
    
    for entry in _groups:
        groups.add(entry["username"])
    
    return list(groups)

def test_user_group_fetching_config(user_dn,resolver_name,dn,attr):
    resolver = _get_group_resolver(resolver_name)
    if not resolver:
        return [] 
    
    base = dn or resolver.basedn
    search_attr = attr or "member"
    groups = _fetch_groups(user_dn,resolver,base,search_attr)
    return groups

def get_user_groups(user_dn):
    """Retrieves the groups that the user belongs to

    Args:
        user_dn (str): the DN of the user

    Returns:
        list: the groups retrieved
    """
    resolver = _get_group_resolver()
    if not resolver:
        return []

    base = get_from_config(LDAP_USER_GROUP_DN_STR,default=resolver.basedn)
    search_attr = get_from_config(LDAP_USER_GROUP_SEARCH_ATTR_STR,default="member")
    
    groups = _fetch_groups(user_dn,resolver,base,search_attr)
    return groups

def get_ip_risk_score(ip: str):
    """Retrieves the risk score for the IP

    Args:
        ip (str): the IP address

    Returns:
        float: the risk score defined for the IP. If the IP does not have a risk score defined, then the subnet with the highest network mask
        to which the IP is part of is returned. If there is no subnet that covers the IP then the default IP risk score is returned.
    """
    default = float(get_from_config("DefaultIPRiskScore",default=DEFAULT_IP_RISK))
    
    if not ip:
        return default
    
    ips = get_risk_scores(CONFIG_IP_RISK_SCORES_KEY)
    subnets = [ipaddress.ip_network(ip) for ip,_ in ips]

    if len(subnets) == 0:
        return default
    
    #get all subnets that hold the ip
    subnets = [subn for subn in subnets if _matches_subnet(ip,subn)]

    if len(subnets) == 0:
        return default
    
    subnet_highest_mask = _get_subnet_with_highest_mask(subnets)
    #fetch the risk score for the subnet
    ip_risk_score = get_risk_score(subnet_highest_mask,CONFIG_IP_RISK_SCORES_KEY)
    return ip_risk_score

def get_service_risk_score(service: str):
    """Retrieves the risk score for the service

    Args:
        service (str): the service name

    Returns:
        float: the risk score defined for the service. If the service does not have a risk score defined, then
        the default service risk score is returned.
    """
    default = float(get_from_config("DefaultServiceRiskScore",default= DEFAULT_SERVICE_RISK))
    
    if not service:
        return default
    
    service_risk_score = get_risk_score(service,CONFIG_SERVICES_RISK_SCORES_KEY)
        
    if service_risk_score == None:
        return default
    
    return service_risk_score

def get_user_risk_score(ugroups: list):
    """Retrieves the highest risk score of the groups 

    Args:
        ugroups (list): the groups of the user

    Returns:
        float: the highest risk score from all of the risk scores of the groups 
    """
    default = float(get_from_config("DefaultUserRiskScore",default=DEFAULT_USER_RISK))
    
    if not ugroups:
        return default
    
    groups = []
    for t in ugroups:
        score = get_risk_score(t,CONFIG_GROUPS_RISK_SCORES_KEY)
        if score:
            groups.append((t,score)) 
            
    if len(groups) == 0:
        log.debug(f"No risk scores found for groups {ugroups}")
        return default
        
    # sorts in ascending order, based on the risk score
    scores = sorted(groups,key=lambda tp: tp[1])
    log.debug(f"Scores: {scores}")
    
    log.debug(f"Using score defined for type {scores[-1][0]}: {scores[-1][1]}")
    # fetch the highest risk score
    user_risk_score = scores[-1][1]
        
    return user_risk_score

#possibly cache the result
def get_risk_score(key: str,config_key: str):
    groups_str: str = get_from_config(config_key)
    groups = groups_str.split(",") if groups_str else []
    if len(groups) == 0:
        return None
    
    exists,i = _check_if_key_exists(key,groups)
    
    if not exists:
        return None
    
    mch = match(rf"{key};(\d+(\.\d+)?)",groups[i])
    score = float(mch.group(1))
    
    return score

def get_risk_scores(config_key: str):
    groups_str: str = get_from_config(config_key)
    groups = groups_str.split(",") if groups_str else []
    
    return [tuple(group.split(";")) for group in groups]

def save_risk_score(key: str,risk_score: str,config_key: str):
    score = sanitize_risk_score(risk_score)
    groups_str: str = get_from_config(config_key)
    groups = groups_str.split(",") if groups_str else []
    exists,_ = _check_if_key_exists(key,groups)
    
    if exists:
        return ParameterError(f"{key} already has a risk score. Please remove it first.")
    
    groups.append(f"{key};{score}")
    set_privacyidea_config(config_key,",".join(groups),typ="public")
    
def remove_risk_score(key: str,config_key: str):
    groups_str = get_from_config(config_key)
    groups = groups_str.split(",") if groups_str else []
    exists,i = _check_if_key_exists(key,groups)
    
    if not exists:
        return ParameterError(f"{key} does not exist")
    
    groups.pop(i)
    set_privacyidea_config(config_key,",".join(groups),typ="public")
    
def sanitize_risk_score(risk_score):
    """Checks if the risk score is a positive number.

    Args:
        risk_score (Any): the risk score to be sanitized

    Raises:
        ParameterError: if risk score is not a number or if its a negative number

    Returns:
        float: the risk score
    """
    try:
        risk_score = float(risk_score)
    except:
        raise ParameterError("Risk score must be a number")
    
    if risk_score < 0:
        raise ParameterError("Risk score must be a positive number")
    
    return risk_score

def ip_version(subnet):
    try:
        ipaddress.IPv4Network(subnet)
        return 4
    except:    
        try:
            ipaddress.IPv6Network(subnet)
            return 6
        except:
            return 0
    
def _get_group_resolver(resolver_name=None):
    rname = resolver_name or get_from_config(LDAP_GROUP_RESOLVER_NAME_STR)
    if not rname:
        log.info("Name for group resolver not set. User group can not be fetched.")
        return None
    
    resolver: IdResolver = get_resolver_object(rname)
    
    if not resolver:
        log.error("Can not find resolver with name {0!s}!",rname)
        
    return resolver 

def _fetch_groups(user_dn,resolver,base,search_attr):
    search_filter = f"({search_attr}={user_dn})"
    entries = resolver._search(base,search_filter,resolver.loginname_attribute)
    
    if len(entries) == 0:
        log.debug(f"Found 0 entries for group search. Base: {base}. Attr: {search_attr}. Filter: {search_filter}")
        return []
    
    groups = set()
    for entry in entries:
        attrs = entry.get("attributes", {})
        for loginname in resolver.loginname_attribute:
            name = attrs.get(loginname,"")
            if name:
                groups.update(name)
    
    log.debug(f"Found groups: {list(groups)}")
    return list(groups)

def _check_if_key_exists(key: str,elements: list):
    for i,element in enumerate(elements):
        mch = match(rf"{key};(\d+(\.\d+)?)",element)
        if mch:
            log.info(f"found match! {mch.groups()}")
            return True,i
            
    return False,None   

def _ip_to_int(ip):
    return int(ipaddress.ip_address(ip))

def _matches_subnet(ip, subnet):
    ip_int = _ip_to_int(ip)
    network_int = _ip_to_int(subnet.network_address)
    netmask_int = _ip_to_int(subnet.netmask)
    
    # Apply bitwise AND to the IP and the subnet mask, then compare to the network address
    return (ip_int & netmask_int) == (network_int & netmask_int)

def _get_subnet_with_highest_mask(subnets):
    return max(subnets,key=lambda subnet: _ip_to_int(subnet.network_address))
