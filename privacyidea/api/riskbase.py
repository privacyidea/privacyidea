from flask import (Blueprint, request)

from privacyidea.lib.error import AuthError, ParameterError, PolicyError, ResourceNotFoundError, privacyIDEAError
from privacyidea.api.lib.utils import required,send_result,getParam
from privacyidea.lib.config import get_token_types
from privacyidea.lib.resolver import get_resolver_list
from privacyidea.lib.riskbase import CONFIG_GROUPS_RISK_SCORES_KEY,CONFIG_IP_RISK_SCORES_KEY,CONFIG_SERVICES_RISK_SCORES_KEY, get_group_resolvers,ip_version,calculate_risk,get_groups,get_risk_scores, remove_group_resolver, save_group_resolver,save_risk_score,remove_risk_score
from privacyidea.api.before_after import after_request, auth_error, before_admin_request, internal_error, not_implemented_error, policy_error, privacyidea_error, resource_not_found_error

class RiskBaseBlueprint(Blueprint):
    def __init__(self):
        super().__init__("riskbase_blueprint", __name__)
        self.after_request(after_request)
        self.before_request(before_admin_request)
        self.app_errorhandler(PolicyError)(policy_error)
        self.app_errorhandler(ResourceNotFoundError)(resource_not_found_error)
        self.app_errorhandler(privacyIDEAError)(privacyidea_error)
        self.app_errorhandler(NotImplementedError)(not_implemented_error)
        self.app_errorhandler(500)(internal_error)
        self.app_errorhandler(AuthError)(auth_error)
        
        #declare routes
        self.route("/",methods=["GET"])(self.get_risk_config)
        self.route("/groups",methods=["POST"])(self.attach_group_resolver)
        self.route("/check",methods=["POST"])(self.check)
        self.route("/user",methods=["POST"])(self.set_user_risk)
        self.route("/service",methods=["POST"])(self.set_service_risk)
        self.route("/ip",methods=["POST"])(self.set_ip_risk)
        self.route("/user/delete",methods=["POST"])(self.delete_user_risk)
        self.route("/service/delete",methods=["POST"])(self.delete_service_risk)
        self.route("/ip/delete",methods=["POST"])(self.delete_ip_risk)
        self.route("/groups/delete",methods=["POST"])(self.delete_user_group_resolvers)
        
    def get_risk_config(self):
        """
        Retrieves all information related to the risk-base page:
        
        user_groups - all groups of users
        
        token_types- all token types that privacyIDEA has
        
        group_resolver - the base ldap resolver that is used to search for user groups
        
        user_group_dn - the base LDAP DN that is used to search the group that a user belongs to
        
        user_group_attr - The name of the LDAP attribute that, along with the user DN, is used to fetch the groups 
        the user belongs to. Used in the search filter.
        
        user_risk - the user types and their defined risk scores
        
        service_risk - the services and their defined risk scores
        
        ip_risk - the ips and their defined risk scores 
        """
        users = get_risk_scores(CONFIG_GROUPS_RISK_SCORES_KEY)
        services = get_risk_scores(CONFIG_SERVICES_RISK_SCORES_KEY)
        ips = get_risk_scores(CONFIG_IP_RISK_SCORES_KEY)
        group_resolvers = get_group_resolvers()

        r = {}
        
        r["user_groups"] = get_groups()
        r["token_types"] = get_token_types()
        resolvers = get_resolver_list()
        r["resolvers"] = list(resolvers.keys())
        
        
        if len(group_resolvers) > 0:
            r["group_resolvers"] = [{"user_resolver": entry[0], "group_resolver": entry[1]} for entry in group_resolvers]
            
        if len(users) > 0:
            r["user_risk"] = [{"group": entry[0], "risk_score": entry[1]} for entry in users]
        
        if len(services) > 0:
            r["service_risk"] = [{"name": entry[0], "risk_score": entry[1]} for entry in services]
        
        if len(ips) > 0 :
            r["ip_risk"] = [{"ip": entry[0], "risk_score": entry[1]} for entry in ips]
        
        return send_result(r)
    
    def attach_group_resolver(self):
        """
        Attachs the group resolver to the user resolver
        
        :jsonparam group_resolver_name: The name of the base LDAP resolver to be used to fetch groups
        :jsonparam user_resolver_name: The name of the LDAP user resolver to be attached to this group resolver
        """
        params = request.all_data
        group_resolver_name = getParam(params,"group_resolver_name",required,allow_empty=False)
        user_resolver_name = getParam(params,"user_resolver_name",required,allow_empty=False)
        
        if group_resolver_name == user_resolver_name:
            raise ParameterError("Group resolver and User resolver cannot be the same")

        resolvers = get_resolver_list()
        resolver_names = resolvers.keys()
        
        if group_resolver_name not in resolver_names:
            raise ParameterError("Group resolver does not exist")
        
        if user_resolver_name not in resolver_names:
            raise ParameterError("User resolver does not exist")

        save_group_resolver(group_resolver_name,user_resolver_name)
            
        return send_result(True)
        
    def check(self):
        """
        Calculates the risk score based on the provided user, service and IP.
        
        Used for testing the configuration.
        
        :jsonparam user: the user group that is used to calculate the risk for the test
        :jsonparam service: the service that is used to calculate the risk for the test
        :jsonparam ip: the IP that is used to calculate the risk for the test
        
        :return: JSON with risk score calculated
        """
        params = request.all_data
        userType = getParam(params,"user")
        service = getParam(params,"service")
        ip = getParam(params,"ip")
        
        r = calculate_risk(ip,service,[userType] if userType != None else None)
        
        return send_result(r)
    
    def set_user_risk(self):
        """
        Sets the risk score for a group of users
        
        :jsonparam user_group: the group to which the risk score will be attached
        :jsonparam risk_score: the risk score for the user group
        """
        
        param = request.all_data
        user_group = getParam(param,"user_group",required,allow_empty=False)
        score = getParam(param,"risk_score",required,allow_empty=False)
        
        save_risk_score(user_group,score,CONFIG_GROUPS_RISK_SCORES_KEY)
        
        return send_result(True)
    
    def set_service_risk(self):
        """
        Sets the risk score for a service
        
        :jsonparam service: the service to which the risk score will be attached
        :jsonparam risk_score: the risk score for the service
        """
        param = request.all_data
        service = getParam(param,"service",required,allow_empty=False)
        score = getParam(param,"risk_score",required,allow_empty=False)
        
        save_risk_score(service,score,CONFIG_SERVICES_RISK_SCORES_KEY)
        
        return send_result(True)
    
    def set_ip_risk(self):
        """
        Set the risk score for an IP or subnet
        
        :jsonparam ip: the ip or subnet address
        :jsonparam riskscore: the risk score for the subnet or IP
        """
        param = request.all_data
        ip: str = getParam(param,"ip",required,allow_empty=False)
        risk_score = getParam(param,"risk_score",required,allow_empty=False)
        
        version = ip_version(ip)
        
        if version == 0:
            raise ParameterError("Invalid IP address or network")

        tmp = ip.split("/")
        mask = None
        if len(tmp) > 1:
            mask = int(tmp[1])
            ip = tmp[0]
        
        if not mask:
            mask = 32 if version == 4 else 128
            
        ip = f"{ip}/{mask}"
        save_risk_score(ip,risk_score,CONFIG_IP_RISK_SCORES_KEY)

        return send_result(True)
    
    def delete_user_risk(self):
        """
        Deletes the risk score attached to the user group
        
        :jsonparam identifier: the name of the group
        """
        param = request.all_data
        identifier = getParam(param,"identifier",required,allow_empty=False)
        
        remove_risk_score(identifier,CONFIG_GROUPS_RISK_SCORES_KEY)
        
        return send_result(True)
    
    def delete_service_risk(self):
        """
        Deletes the risk score attached to the service
        
        :jsonparam identifier: the name of the service
        """
        param = request.all_data
        identifier = getParam(param,"identifier",required,allow_empty=False)
        
        remove_risk_score(identifier,CONFIG_SERVICES_RISK_SCORES_KEY)
        
        return send_result(True)
    
    def delete_ip_risk(self):
        """
        Deletes the risk score attached to the IP or subnet
        
        :jsonparam identifier: the IP or subnet
        """
        param = request.all_data
        identifier = getParam(param,"identifier",required,allow_empty=False)
        
        remove_risk_score(identifier,CONFIG_IP_RISK_SCORES_KEY)
        
        return send_result(True)
    
    def delete_user_group_resolvers(self):
        param = request.all_data
        user_resolver = getParam(param,"user_resolver_name",required,allow_empty=False)
        group_resolver = getParam(param,"group_resolver_name",required,allow_empty=False)
        
        remove_group_resolver(group_resolver,user_resolver)
        
        return send_result(True)
        
riskbase_blueprint = RiskBaseBlueprint()