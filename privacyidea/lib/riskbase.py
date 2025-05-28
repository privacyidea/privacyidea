import ipaddress
import logging
from privacyidea.lib.error import ParameterError
from privacyidea.lib.resolver import get_resolver_object
from privacyidea.lib.resolvers.LDAPIdResolver import IdResolver
from privacyidea.lib.config import get_from_config,set_privacyidea_config,delete_privacyidea_config
from re import match

DEFAULT_USER_RISK = 3
DEFAULT_IP_RISK = 1
DEFAULT_SERVICE_RISK = 5

CONFIG_GROUPS_RISK_SCORES_KEY = "user_groups_risk_scores"
CONFIG_SERVICES_RISK_SCORES_KEY = "services_risk_scores"
CONFIG_IP_RISK_SCORES_KEY = "ip_risk_scores"
CONFIG_GROUP_RESOLVERS_KEY = "user_group_resolvers"

config_key_to_prefix = {
    CONFIG_IP_RISK_SCORES_KEY: "ip",
    CONFIG_GROUPS_RISK_SCORES_KEY: "group",
    CONFIG_SERVICES_RISK_SCORES_KEY: "service"
}


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
    groups = set()
    resolver_names = get_group_resolvers()
    for rname in resolver_names:
        resolvers = _get_group_resolvers(rname[0])
        if not resolvers:
            return []
        
        for resolver in resolvers:
            _groups = resolver.getUserList({})
            
            for entry in _groups:
                groups.add(entry["username"])
    
    return list(groups)

def get_user_groups(user_dn,user_resolver_name):
    """Retrieves the groups that the user belongs to

    Args:
        user_dn (str): the DN of the user

    Returns:
        list: the groups retrieved
    """
    resolvers = _get_group_resolvers(user_resolver_name)
    if not resolvers:
        return []

    groups = []
    for resolver in resolvers:
        groups.extend(_fetch_groups(user_dn,resolver))
        
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
    
    subnet_highest_mask = max(subnets,key=lambda subnet: subnet.prefixlen)
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
        if score is not None:
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
    _key = f"{config_key_to_prefix[config_key]}_{key}"
    score = get_from_config(_key)
    
    return float(score) if score else None

def get_risk_scores(config_key: str):
    groups_str: str = get_from_config(config_key)
    groups = groups_str.split(",") if groups_str else []
    
    return [(group, get_from_config(f"{config_key_to_prefix[config_key]}_{group}")) for group in groups]

def save_risk_score(key: str,risk_score: str,config_key: str):
    _key = f"{config_key_to_prefix[config_key]}_{key}"
    if get_from_config(_key):
        raise ParameterError(f"{key} already has a risk score. Please remove it first.")

    score = sanitize_risk_score(risk_score)
    groups_str: str = get_from_config(config_key)
    groups = groups_str.split(",") if groups_str else []
    groups.append(key)
    
    set_privacyidea_config(_key,score)
    set_privacyidea_config(config_key,",".join(groups),typ="public")
    
def remove_risk_score(key: str,config_key: str):
    _key = f"{config_key_to_prefix[config_key]}_{key}"
    if not get_from_config(_key):
        raise ParameterError(f"{key} does not exist")
    
    groups_str = get_from_config(config_key)
    groups = groups_str.split(",") if groups_str else []
    groups.remove(key)
    
    set_privacyidea_config(config_key,",".join(groups),typ="public")
    delete_privacyidea_config(_key)
    
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
        
def get_group_resolvers():
    resolvers_str: str = get_from_config(CONFIG_GROUP_RESOLVERS_KEY)
    resolvers = resolvers_str.split(",") if resolvers_str else []
    return [tuple(s.split(";")) for s in resolvers]
        
def save_group_resolver(group_resolver_name,user_resolver_name):
    groups_str: str = get_from_config(CONFIG_GROUP_RESOLVERS_KEY)
    groups = groups_str.split(",") if groups_str else []
    exists,_ = _check_if_group_exists(group_resolver_name,user_resolver_name,groups)
    
    if exists:
        raise ParameterError(f"{group_resolver_name} already has a user resolver attached. Please remove it first.")
    
    groups.append(f"{user_resolver_name};{group_resolver_name}")
    set_privacyidea_config(CONFIG_GROUP_RESOLVERS_KEY,",".join(groups),typ="public")
    
def remove_group_resolver(group_resolver_name,user_resolver_name):
    groups_str = get_from_config(CONFIG_GROUP_RESOLVERS_KEY)
    groups = groups_str.split(",") if groups_str else []
    exists,group_indexs = _check_if_group_exists(group_resolver_name,user_resolver_name,groups)
    
    if not exists:
        raise ParameterError(f"{user_resolver_name} is not attached to {group_resolver_name}")
    
    for i in group_indexs:
        groups.pop(i)
        
    set_privacyidea_config(CONFIG_GROUP_RESOLVERS_KEY,",".join(groups),typ="public")
    
def _get_group_resolver_names(user_resolver_name):
    groups_str: str = get_from_config(CONFIG_GROUP_RESOLVERS_KEY)
    groups = groups_str.split(",") if groups_str else []
    if len(groups) == 0:
        return None
    
    exists,group_indexs = _check_if_group_exists(".*",user_resolver_name,groups)
    
    if not exists:
        return None
    
    gs = []
    for i in group_indexs:
        mch = match(rf"{user_resolver_name};(.*)",groups[i])
        gs.append(mch.group(1))
        
    return gs
    
def _get_group_resolvers(resolver_name):
    rnames = _get_group_resolver_names(resolver_name)
    if not rnames:
        log.info("Name for group resolver not set. User group can not be fetched.")
        return None
    
    resolvers = []
    
    for rname in rnames:
        resolver: IdResolver = get_resolver_object(rname)
    
        if not resolver:
            log.error(f"Can not find resolver with name {rname}!")
            continue
        
        resolvers.append(resolver)  
        
    return resolvers

def _fetch_groups(user_dn,resolver: IdResolver):
    entries = resolver.getUserList({"member": user_dn})
    
    if len(entries) == 0:
        return []

    groups = set()
    for entry in entries:
        name = entry.get("username",None)
        if name:
            groups.add(name)
    
    log.debug(f"Found groups: {list(groups)}")
    return list(groups)

def _check_if_group_exists(group_resolver: str,user_resolver: str,groups: list):
    gs = []
    for i,element in enumerate(groups):
        mch = match(rf"{user_resolver};{group_resolver}",element)
        if mch:
            log.debug(f"found match! {mch.groups()}")
            gs.append(i)

    if len(gs) == 0:            
        return False,None  
    
    return True,gs

def _matches_subnet(ip, subnet):
    ip_int = int(ipaddress.ip_address(ip))
    network_int = int(ipaddress.ip_address(subnet.network_address))
    netmask_int = int(ipaddress.ip_address(subnet.netmask))
    
    # Apply bitwise AND to the IP and the subnet mask, then compare to the network address
    return (ip_int & netmask_int) == (network_int & netmask_int)