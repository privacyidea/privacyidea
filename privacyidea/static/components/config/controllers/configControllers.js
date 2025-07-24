/**
 * http://www.privacyidea.org
 * (c) cornelius kölbel, cornelius@privacyidea.org
 *
 * 2015-01-11 Cornelius Kölbel, <cornelius@privacyidea.org>
 *
 * This code is free software; you can redistribute it and/or
 * modify it under the terms of the GNU AFFERO GENERAL PUBLIC LICENSE
 * License as published by the Free Software Foundation; either
 * version 3 of the License, or any later version.
 *
 * This code is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU AFFERO GENERAL PUBLIC LICENSE for more details.
 *
 * You should have received a copy of the GNU Affero General Public
 * License along with this program.  If not, see <http://www.gnu.org/licenses/>.
 *
 */
myApp.controller("policyListController", ["$scope", "$stateParams", "$location",
    "ConfigFactory",
    function ($scope, $stateParams,
              $location, ConfigFactory) {
        if ($location.path() === "/config/policies") {
            $location.path("/config/policies/list");
        }
        $('html,body').scrollTop(0);

        // Get all policies
        $scope.getPolicies = function () {
            ConfigFactory.getPolicies(function (data) {
                $scope.policies = data.result.value;
                //debug: console.log("Fetched all policies");
                //debug: console.log($scope.policies);

                // converts action object to string and creates new list "action_desc"
                $scope.policies.forEach(function (value, i) {
                    $scope.policies[i]['action_desc'] = [];
                    for (const [key, value] of Object.entries($scope.policies[i]['action'])) {
                        $scope.policies[i]['action_desc'].push((`${key}: ${value}`));
                    }
                });
            });
        };

        $scope.delPolicy = function (policyName) {
            ConfigFactory.delPolicy(policyName, function (data) {
                $scope.getPolicies();
            });
        };

        // define functions
        $scope.enablePolicy = function (name) {
            ConfigFactory.enablePolicy(name, function () {
                $scope.getPolicies();
            });
        };

        $scope.disablePolicy = function (name) {
            ConfigFactory.disablePolicy(name, function () {
                $scope.getPolicies();
            });
        };

        $scope.priorityChanged = function (policy) {
            ConfigFactory.setPolicy(policy.name, policy, function () {
                $scope.getPolicies();
            });
        };

        $scope.getPolicies();

        // listen to the reload broadcast
        $scope.$on("piReload", $scope.getPolicies);
    }]);

myApp.controller("policyDetailsController", ["$scope", "$stateParams",
    "ConfigFactory", "$state",
    "PolicyTemplateFactory",
    function ($scope, $stateParams,
              ConfigFactory, $state,
              PolicyTemplateFactory) {
        // init
        $scope.realms = [];
        $scope.adminRealms = [];
        $scope.resolvers = [];
        $scope.pinodes = [];
        $scope.realmsLoaded = false;
        $scope.resolversLoaded = false;
        $scope.adminRealmsLoaded = false;
        $scope.policyDefsLoaded = false;
        $scope.pinodesLoaded = false;
        $scope.policyConditionDefsLoaded = false;
        $scope.scopes = [];
        $scope.selectedScope = null;
        $scope.viewPolicyTemplates = false;
        $scope.action_filter = "";
        $('html,body').scrollTop(0);
        $scope.onlySelectedVisible = false;

        $scope.userAgentsMapping = {
            "Credential Provider": "privacyidea-cp",
            "Keycloak": "privacyIDEA-Keycloak",
            "AD FS": "PrivacyIDEA-ADFS",
            "SimpleSAMLphp": "simpleSAMLphp",
            "PAM": "PAM",
            "Shibboleth": "privacyIDEA-Shibboleth",
            "Nextcloud": "privacyidea-nextcloud",
            "FreeRADIUS": "FreeRADIUS",
            "LDAP Proxy": "privacyIDEA-LDAP-Proxy",
            "privacyIDEA Authenticator": "privacyIDEA-App"
        };
        $scope.userAgents = [];
        angular.forEach($scope.userAgentsMapping, function (value, key) {
            $scope.userAgents.push({"name": key, "identifier": value, "ticked": false});
        });
        $scope.selectedUserAgents = {};
        $scope.customUserAgent = "";

        $scope.addCustomUserAgent = function () {
            if ($scope.customUserAgent) {
                $scope.userAgents.push({
                    "name": $scope.customUserAgent,
                    "identifier": $scope.customUserAgent,
                    "ticked": true
                });
                $scope.customUserAgent = "";
            }
        };

        let check_all_loaded = function () {
            if ($scope.resolversLoaded &&
                $scope.adminRealmsLoaded &&
                $scope.realmsLoaded &&
                $scope.policyDefsLoaded &&
                $scope.pinodesLoaded &&
                $scope.policyConditionDefsLoaded) {
                $scope.presetEditValues();
            }
        };

        // define functions
        $scope.enablePolicy = function (name) {
            ConfigFactory.enablePolicy(name, function () {
                $scope.params.active = true;
                $scope.getPolicies();
            });
        };

        $scope.disablePolicy = function (name) {
            ConfigFactory.disablePolicy(name, function () {
                $scope.params.active = false;
                $scope.getPolicies();
            });
        };

        $scope.delPolicy = function (policyName) {
            ConfigFactory.delPolicy(policyName, function (data) {
                $scope.getPolicies();
                $state.go("config.policies.list");
            });
        };

        // Get the policy templates from github
        PolicyTemplateFactory.getTemplates(function (data) {
            //debug: console.log("Getting Policy Templates.");
            //debug: console.log(data);
            $scope.policyTemplates = data;
        });

        $scope.getTemplate = function (templateName) {
            PolicyTemplateFactory.getTemplate(templateName, function (data) {
                //debug: console.log("Get template ". templateName);
                //debug: console.log(data);
                // Set template data.
                $scope.policyname = data.name;
                $scope.presetEditValues2({
                    name: data.name,
                    scope: data.scope,
                    realm: data.realm || [],
                    action: data.action || [],
                    resolver: data.resolver || [],
                    adminrealm: data.adminrealm || [],
                    conditions: data.conditions || [],
                    pinode: []
                });
            });
        };

        // get init values from the server
        ConfigFactory.getPolicyDefs(function (data) {
            $scope.policyDefs = data.result.value;
            //debug: console.log($scope.policyDefs);
            // fill the scope:
            angular.forEach($scope.policyDefs, function (value, key) {
                $scope.scopes.push({name: key, ticked: false});
            });
            $scope.policyDefsLoaded = true;
            check_all_loaded();
        });
        ConfigFactory.getPolicyConditionDefs(function (data) {
            $scope.policyConditionDefs = data.result.value;
            $scope.policyConditionDefsLoaded = true;
            check_all_loaded();
        });
        ConfigFactory.getPINodes(function (data) {
            $scope.pinodes = [];
            angular.forEach(data.result.value, function (node) {
                $scope.pinodes.push({name: node.name, uuid: node.uuid, ticked: false});
            });
            $scope.pinodesLoaded = true;
            check_all_loaded();
        });

        ConfigFactory.getRealms(function (data) {
            const realms = data.result.value;
            angular.forEach(realms, function (value, key) {
                $scope.realms.push({name: key, ticked: false});
            });
            // after everything is loaded, we can preset the values
            $scope.realmsLoaded = true;
            check_all_loaded();
        });
        ConfigFactory.getAdminRealms(function (data) {
            const adminRealms = data.result.value;
            angular.forEach(adminRealms, function (value, key) {
                $scope.adminRealms.push({name: value, ticked: false});
            });
            $scope.adminRealmsLoaded = true;
            check_all_loaded();
        });
        ConfigFactory.getResolvers(function (data) {
            const resolvers = data.result.value;
            angular.forEach(resolvers, function (value, key) {
                $scope.resolvers.push({name: key, ticked: false});
            });
            // after realms and resolvers have loaded, we can preset the policy values
            $scope.resolversLoaded = true;
            check_all_loaded();
        });

        $scope.existingPolicyname = $stateParams.policyname;
        if ($scope.existingPolicyname) {
            $scope.policyname = $scope.existingPolicyname;
        }

        $scope.fillActionList = function (scope, policyActions) {
            // Each time the scope is changed, we need to fill the
            // action dropdown.
            // in the case of action values, we need to provide a list of
            // checkboxes and input fields.
            // we can do this with include files like at token.enroll
            //debug: console.log(scope);
            //debug: console.log($scope.policyDefs);
            const actions = $scope.policyDefs[scope];
            //debug: console.log(actions);
            $scope.actions = [];
            $scope.actionGroups = [];
            $scope.isActionValues = false;
            // Reset number of opened action groups
            $scope.groupsOpen = 0;
            $scope.groupIsOpen = {};

            angular.forEach(actions, function (value, key) {
                // we might evaluate value.group and group the actions
                if ($scope.actionGroups.indexOf(value.group) < 0) {
                    // build a list of all groups
                    $scope.actionGroups.push(value.group);
                    $scope.groupIsOpen[value.group] = false;
                }
                // Check the given policy actions
                let ticked = false;
                if (policyActions && policyActions[key] === true) {
                    ticked = true;
                }
                $scope.actions.push({name: key, help: value.desc, ticked: ticked});
                // Check if we need to do actionValues
                if (value.type !== "bool") {
                    $scope.isActionValues = true;
                }
            });

            if ($scope.isActionValues) {
                // This holds the array of actionValues
                $scope.actionValuesStr = {};
                $scope.actionValuesNum = {};
                $scope.actionCheckBox = {};
                $scope.actionValuesText = {};
                $scope.actions = [];
                // This scope contains action values. We need to create
                // a list of checkboxes and input fields.
                angular.forEach(actions, function (value, key) {
                    let val = [];
                    // handle select with multiple options
                    if (value.multiple === true) {
                        value.value.forEach(function (entry) {
                            val.push({
                                'name': entry,
                                'ticked': false
                            });
                        });
                    } else
                        val = value.value;

                    $scope.actions.push({
                        name: key,
                        type: value.type,
                        desc: value.desc,
                        group: value.group,
                        allowedValues: val,
                        multiple: value.multiple
                    });
                    // preset the fields
                    if (policyActions && policyActions[key]) {
                        $scope.actionCheckBox[key] = true;
                        if (policyActions[key] !== true) {
                            if (value.type === "str") {
                                $scope.actionValuesStr[key] = policyActions[key];
                                if (value.multiple === true) {
                                    let vals = $scope.actions.find(x => x.name === key).allowedValues;
                                    policyActions[key].split(' ').forEach(function (n) {
                                        (vals.find(x => x.name === n) || {}).ticked = true;
                                    })
                                }
                            }
                            if (value.type === "int")
                                $scope.actionValuesNum[key] = parseInt(policyActions[key]);
                            if (value.type === "text")
                                $scope.actionValuesText[key] = policyActions[key];
                        }
                    }
                });
            }
        };

        $scope.params = {
            action: "",
            scope: "",
            realm: "",
            resolver: "",
            user: "",
            active: true,
            check_all_resolvers: false,
            user_case_insensitive: false,
            client: "",
            time: "",
            description: "",
            priority: 1,
            conditions: [],
            pinode: [],
            user_agents: []
        };

        function _buildParamsForSave(targetName) {
            const p = angular.copy($scope.params);
            // get scope
            p.scope = $scope.selectedScope[0].name;
            p.name = targetName;
            p.action = [];
            p.realm = [];
            p.resolver = [];
            p.adminrealm = [];
            p.pinode = [];
            p.user_agents = [];

            // get actions
            if ($scope.isActionValues) {
                // we need to process the value-actions
                // iterate through the checkboxes
                angular.forEach($scope.actionCheckBox, function (checked, key) {
                    if (!checked) {
                        return;
                    }
                    // The action is checked. So try to get an action value.
                    // The type is given in the $scope.actions array
                    // It is either a string/text, a num or only a bool
                    const meta = $scope.actions.find(o => o.name === key);
                    switch (meta.type) {
                        case "bool":
                            p.action.push(key);
                            break;
                        case "int":
                            p.action.push(key + "=" + $scope.actionValuesNum[key]);
                            break;
                        case "text":
                            p.action.push(key + "=" + $scope.actionValuesText[key]);
                            break;
                        case "str":
                            const val = $scope.actionValuesStr[key];
                            if (Array.isArray(val)) {
                                p.action.push(key + "=" + val.map(v => v.name).join(" "));
                            } else {
                                p.action.push(key + "=" + val);
                            }
                            break;
                        default:
                            console.error('Unknown policy value type: ' + meta.type);
                    }
                });
            } else {
                // We only have boolean actions...
                angular.forEach($scope.selectedActions, function (a) {
                    p.action.push(a.name);
                });
            }
            // get realms
            angular.forEach($scope.selectedRealms, r => p.realm.push(r.name));
            // get resolvers
            angular.forEach($scope.selectedResolvers, r => p.resolver.push(r.name));
            // get admin realms
            angular.forEach($scope.selectedAdminRealms, r => p.adminrealm.push(r.name));
            // get PINodes
            angular.forEach($scope.selectedPINodes, n => p.pinode.push(n.name));
            // get user agents
            angular.forEach($scope.selectedUserAgents, agent => p.user_agents.push(agent.identifier));
            return p;
        }

        $scope.createPolicy = function () {
            // This is called to save the policy
            const paramsToSave = _buildParamsForSave($scope.policyname);
            ConfigFactory.setPolicy($scope.policyname, paramsToSave, function () {
                // Return to the policy list
                $scope.getPolicies();
                $state.go("config.policies.list");
            });
            // Jump to top when the policy is saved
            $('html,body').scrollTop(0);
        };

        $scope.renamePolicy = function (oldName, newName) {
            if (!newName || newName === oldName) {
                return;
            }

            ConfigFactory.renamePolicy(oldName, newName, function (data) {
                if (data.result.status === true) {
                    // Reload the policy list and the details page of the policy
                    $scope.getPolicies();
                    $state.go("config.policies.details", {
                        'policyname': $scope.policyname
                    });
                }
            });
        };

        $scope.presetEditValues2 = function (policy) {
            //debug: console.log(policy);
            // fill $scope.params
            $scope.params.user = policy.user;
            $scope.params.adminuser = policy.adminuser;
            $scope.params.active = policy.active;
            $scope.params.check_all_resolvers = policy.check_all_resolvers;
            $scope.params.user_case_insensitive = policy.user_case_insensitive;
            $scope.params.client = policy.client;
            $scope.params.time = policy.time;
            $scope.params.priority = policy.priority;
            $scope.params.description = policy.description;
            // we need to deep-copy the policy conditions to ensure that we're working on our own copy
            $scope.params.conditions = angular.copy(policy.conditions);
            // tick the realms and the resolvers
            angular.forEach($scope.realms, function (value, key) {
                if (policy.realm.indexOf(value.name) > -1) {
                    $scope.realms[key].ticked = true;
                }
            });
            angular.forEach($scope.resolvers, function (value, key) {
                if (policy.resolver.indexOf(value.name) > -1) {
                    $scope.resolvers[key].ticked = true;
                }
            });
            angular.forEach($scope.adminRealms, function (value, key) {
                if (policy.adminrealm.indexOf(value.name) > -1) {
                    $scope.adminRealms[key].ticked = true;
                }
            });
            angular.forEach($scope.pinodes, function (value, key) {
                if (policy.pinode.indexOf(value.name) > -1) {
                    $scope.pinodes[key].ticked = true;
                }
            });
            angular.forEach($scope.userAgents, function (value, key) {
                if (policy.user_agents.indexOf(value.identifier) > -1) {
                    $scope.userAgents[key].ticked = true;
                }
            });
            angular.forEach($scope.scopes, function (value, key) {
                $scope.scopes[key].ticked = (policy.scope === value.name);
            });
            $scope.fillActionList(policy.scope, policy.action);
        };

        $scope.presetEditValues = function () {
            //debug: console.log("presetEditValues");
            //debug: console.log($scope.policies);
            //debug: console.log($scope.policyDefs);

            if ($scope.policies) {
                // We have $scope.policies, since we come from the state policies.list
                angular.forEach($scope.policies, function (value, key) {
                    if (value.name === $stateParams.policyname) {
                        $scope.presetEditValues2(value);
                    }
                });
            } else {
                // We have no $scope.policies, maybe since we are called directly.
                // So we need to fetch this policy definition
                ConfigFactory.getPolicy($stateParams.policyname, function (data) {
                    var policy = data.result.value[0];
                    $scope.presetEditValues2(policy);
                });
            }
        };

        $scope.openCloseAllGroups = function (open) {
            angular.forEach($scope.actionGroups, function (group) {
                $scope.groupIsOpen[group] = open;
            });
        };

        $scope.groupsOpen = 0;
        $scope.$watch('groupIsOpen', function (newVal, oldVal) {
            if (newVal !== undefined && oldVal !== undefined) {
                angular.forEach(newVal, function (isOpen, group) {
                    if (newVal[group] != oldVal[group]) {
                        if (isOpen) {
                            $scope.groupsOpen++;
                        } else if ($scope.groupsOpen > 0) {
                            $scope.groupsOpen--;
                        }
                    }
                })
            }
        }, true);

        // test if the accordion group should be open or closed
        $scope.checkOpenGroup = function (action, pattern) {
            let pat = escapeRegexp(pattern);
            let re = RegExp(pat, 'i');
            return ($scope.actionCheckBox[action.name] ||
                    !$scope.onlySelectedVisible) &&
                (re.test(action.name) || re.test(action.desc));
        };
    }]);

myApp.controller("tokenConfigController", ["$scope", "$location", "$rootScope",
    "$state", "$stateParams",
    "ConfigFactory", "instanceUrl",
    "inform", "gettextCatalog",
    function ($scope, $location,
              $rootScope, $state,
              $stateParams,
              ConfigFactory, instanceUrl,
              inform, gettextCatalog) {
        $scope.defaultSMSProvider = "privacyidea.lib.smsprovider.HttpSMSProvider.HttpSMSProvider";
        $scope.tokentype = $stateParams.tokentype || "hotp";
        $scope.form = {};
        $scope.original_params = {};
        $scope.instanceUrl = instanceUrl;
        $scope.nextQuestion = 0;
        $scope.formInit = {
            totpSteps: ["30", "60"],
            hashlibs: ["sha1", "sha256", "sha512"],
            smsProviders: [$scope.defaultSMSProvider,
                "privacyidea.lib.smsprovider.SipgateSMSProvider.SipgateSMSProvider",
                "privacyidea.lib.smsprovider.SmtpSMSProvider.SmtpSMSProvider"]
        };

        $scope.loadSystemConfig = function () {
            ConfigFactory.loadSystemConfig(function (data) {
                $scope.form = data.result.value;
                // make a deep copy
                angular.copy($scope.form, $scope.original_params);
                // TODO: We need to put these settings in the token specific code
                // Default inits
                $scope.form['totp.timeStep'] = $scope.form['totp.timeStep'] || "30";
                $scope.form['totp.hashlib'] = $scope.form['totp.hashlib'] || "sha1";
                $scope.form['hotp.hashlib'] = $scope.form['hotp.hashlib'] || "sha1";
                // RADIUS
                $scope.form['radius.secret.type'] = "password";
                $scope.form['radius.dictfile'] = "/etc/privacyidea/dictionary";
                // SMS
                $scope.form['sms.Provider'] = $scope.form['sms.Provider'] || $scope.defaultSMSProvider;
                // Email
                $scope.form['email.password.type'] = "password";
                // We need to convert the values to bools - otherwise we have
                // problems when unchecking a checked checkbox
                $scope.form['email.tls'] = $scope.isChecked($scope.form['email.tls']);
                $scope.form['remote.verify_ssl_certificate'] = $scope.isChecked($scope.form['remote.verify_ssl_certificate']);
                angular.forEach($scope.form, function (value, key) {
                    if (key.indexOf('question.question.') === 0) {
                        const counter = key.split('.')[2];
                        if (counter >= $scope.nextQuestion) {
                            $scope.nextQuestion += 1;
                        }

                    }
                });
            });
        };

        $scope.saveTokenConfig = function () {
            // only save parameters, that have changed!
            //debug: console.log($scope.form);
            const save_params = {};
            angular.forEach($scope.form, function (value, key) {
                if (value != $scope.original_params[key])
                    save_params[key] = value;
            });
            ConfigFactory.saveSystemConfig(save_params, function (data) {
                if (data.result.status === true) {
                    inform.add(gettextCatalog.getString("System Config saved."),
                        {type: "info"});
                }
            });
        };

        $scope.deleteSystemEntry = function (apiId) {
            ConfigFactory.delSystemConfig(apiId, function (data) {
                if (data.result.status === true) {
                    inform.add(gettextCatalog.getString("System entry deleted."),
                        {type: "info"});
                    $scope.loadSystemConfig();
                }
            });
        };

        $scope.yubikeyCreateNewKey = function (apiId) {
            ConfigFactory.getRandom(20, "b64", function (data) {
                $scope.form['yubikey.apiid.' + apiId] = data.result.value;
            });
        };

        $scope.addQuestion = function () {
            $scope.saveTokenConfig();
            $scope.nextQuestion += 1;
        };

        $scope.getSmtpIdentifiers();
        $scope.getSMSIdentifiers();
        $scope.loadSystemConfig();
    }]);

myApp.controller("configController", ["$scope", "$location", "$rootScope",
    "$state", "ConfigFactory", "instanceUrl",
    "inform", "gettextCatalog",
    function ($scope, $location, $rootScope,
              $state, ConfigFactory,
              instanceUrl, inform,
              gettextCatalog) {
        $scope.instanceUrl = instanceUrl;
        $scope.params = {};
        $('html,body').scrollTop(0);
        // go to the system view by default
        if ($location.path() === "/config") {
            $location.path("/config/system");
        }
        if ($location.path() === "/config/system") {
            $location.path("/config/system/edit");
        }
        if ($location.path() === "/config/resolvers") {
            $location.path("/config/resolvers/list");
        }

        $scope.items = ["item1", "item2", "item3"];
        $scope.dragControlListeners = {
            accept: function (sourceItemHandleScope, destSortableScope) {
                return boolean;
            },
            //override to determine drag is allowed or not. default is true.
            itemMoved: function (event) {
                //Do what you want},
            },
            orderChanged: function (event) {
                //Do what you want},
            },
            containment: '#board'//optional param.
        };

        // TODO: This information needs to be fetched from the server
        $scope.availableResolverTypes = ['passwdresolver', 'ldapresolver', 'sqlresolver', 'scimresolver',
            'httpresolver', 'entraidresolver', 'keycloakresolver'];
        // TODO: This information needs to be fetched from the server
        $scope.availableMachineResolverTypes = ['hosts', 'ldap'];
        // TODO: This information needs to be fetched from the server
        $scope.availableCAConnectorTypes = ['local', 'microsoft'];

        $scope.getResolvers = function () {
            ConfigFactory.getResolvers(function (data) {
                $scope.resolvers = data.result.value;
            });
        };

        // Email/SMTP part
        $scope.getSmtpIdentifiers = function () {
            ConfigFactory.getSmtp(function (data) {
                //debug: console.log("SMTP Identifiers");
                //debug: console.log(data.result.value);
                $scope.smtpIdentifiers = data.result.value;
            });
        };

        $scope.getSMSIdentifiers = function () {
            ConfigFactory.getSMSGateways(undefined, function (data) {
                //debug: console.log("SMS Identifiers");
                // Argh when will we have array comprehension?
                // $scope.smsIdentifiers = [sms.name for (sms of data.result.value)];
                $scope.smsIdentifiers = Array();
                angular.forEach(data.result.value, function (sms) {
                    $scope.smsIdentifiers.push(sms.name);
                });
                //debug: console.log($scope.smsIdentifiers);
            });
        };

        $scope.getRADIUSIdentifiers = function () {
            ConfigFactory.getRadius(function (data) {
                $scope.radiusIdentifiers = data.result.value;
            });
        };

        $scope.delResolver = function (name) {
            ConfigFactory.delResolver(name, function (data) {
                $scope.resolvers = data.result.value;
                $scope.getResolvers();
            });
        };

        $scope.getMachineResolvers = function () {
            ConfigFactory.getMachineResolvers(function (data) {
                $scope.machineResolvers = data.result.value;
            });
        };

        $scope.delMachineResolver = function (name) {
            ConfigFactory.delMachineResolver(name, function (data) {
                $scope.machineResolvers = data.result.value;
                $scope.getMachineResolvers();
            });
        };

        $scope.editResolver = function (resolvername, r_type) {
            // change the view to the config.resolvers.edit
            $state.go("config.resolvers.edit" + r_type, {'resolvername': resolvername});
            $rootScope.returnTo = "config.resolvers.list";
        };

        $scope.getResolvers();
        $scope.selectedResolvers = {};
        $scope.selectedPINodes = {};
        $scope.getSmtpIdentifiers();
        $scope.getRADIUSIdentifiers();

        $scope.saveSystemConfig = function () {
            ConfigFactory.saveSystemConfig($scope.params, function (data) {
                //debug: console.log($scope.params);
                //debug: console.log(data);
                inform.add(gettextCatalog.getString("System Config saved."),
                    {type: "info"});
            });
        };
        $scope.getSystemConfig = function () {
            ConfigFactory.getSystemConfig(function (data) {
                //debug: console.log(data);
                $scope.params = data.result.value;
                $scope.params.PrependPin = $scope.isChecked($scope.params.PrependPin);
                $scope.params.no_auth_counter = $scope.isChecked($scope.params.no_auth_counter);
                $scope.params['PrependPin.type'] = "public";
                $scope.params.splitAtSign = $scope.isChecked($scope.params.splitAtSign);
                $scope.params.IncFailCountOnFalsePin = $scope.isChecked($scope.params.IncFailCountOnFalsePin);
                $scope.params.ReturnSamlAttributes = $scope.isChecked($scope.params.ReturnSamlAttributes);
                $scope.params.ReturnSamlAttributesOnFail = $scope.isChecked($scope.params.ReturnSamlAttributesOnFail);
                $scope.params.AutoResync = $scope.isChecked($scope.params.AutoResync);
                $scope.params.UiLoginDisplayHelpButton = $scope.isChecked($scope.params.UiLoginDisplayHelpButton);
                $scope.params.UiLoginDisplayRealmBox = $scope.isChecked($scope.params.UiLoginDisplayRealmBox);

                //debug: console.log($scope.params);
            });
        };

        $scope.getSystemDocumentation = function () {
            ConfigFactory.getDocumentation(function (data) {
                //debug: console.log(data);
                $scope.systemDocumentation = data;
            });
        };
        $scope.getSystemConfig();

        // listen to the reload broadcast
        $scope.$on("piReload", function () {
            $scope.getSystemConfig();
        });

        $scope.deleteUserCache = function () {
            ConfigFactory.deleteUserCache(function (data) {
                if (data.result.status === true) {
                    if (data.result.value.deleted > 0) {
                        inform.add(gettextCatalog.getString(
                                "Total user cache entries deleted: " + data.result.value.deleted),
                            {type: "success", ttl: 4000});
                    } else {
                        inform.add(gettextCatalog.getString(
                                "No user cache entries were deleted."),
                            {type: "info", ttl: 4000});
                    }
                } else {
                    inform.add(gettextCatalog.getString(
                            "Could not delete user cache."),
                        {type: "danger", ttl: 8000});
                }
            });
        };

    }]);

myApp.controller("PasswdResolverController", ["$scope", "ConfigFactory",
    "$state", "$stateParams",
    function ($scope, ConfigFactory,
              $state, $stateParams) {
        $scope.params = {
            type: 'passwdresolver',
            fileName: "/etc/passwd"
        };

        $scope.resolvername = $stateParams.resolvername;
        if ($scope.resolvername) {
            /* If we have a resolvername, we do an Edit
             and we need to fill all the $scope.params */
            ConfigFactory.getResolver($scope.resolvername, function (data) {
                var resolver = data.result.value[$scope.resolvername];
                $scope.params = resolver.data;
                $scope.params.type = 'passwdresolver';
            });
        }

        $scope.setResolver = function () {
            ConfigFactory.setResolver($scope.resolvername, $scope.params, function (data) {
                $scope.set_result = data.result.value;
                $scope.getResolvers();
                $state.go("config.resolvers.list");
            });
        };
    }]);

myApp.controller("hostsResolverController", ["$scope", "ConfigFactory",
    "$state", "$stateParams",
    function ($scope, ConfigFactory,
              $state, $stateParams) {
        $scope.params = {
            type: 'hosts',
            filename: "/etc/hosts"
        };

        $scope.resolvername = $stateParams.resolvername;
        if ($scope.resolvername) {
            /* If we have a resolvername, we do an Edit
             and we need to fill all the $scope.params */
            ConfigFactory.getMachineResolver($scope.resolvername, function (data) {
                var resolver = data.result.value[$scope.resolvername];
                $scope.params = resolver.data;
                $scope.params.type = 'hosts';
            });
        }

        $scope.setMachineResolver = function () {
            ConfigFactory.setMachineResolver($scope.resolvername, $scope.params, function (data) {
                $scope.set_result = data.result.value;
                $scope.getMachineResolvers();
                $state.go("config.mresolvers.list");
            });
        };
    }]);

myApp.controller("CAConnectorController", ["$scope", "ConfigFactory", "$state",
    "$rootScope", "$location",
    function ($scope, ConfigFactory,
              $state, $rootScope,
              $location) {
        if ($location.path() === "/config/caconnectors") {
            $location.path("/config/caconnectors/list");
        }

        $scope.getCAConnectors = function () {
            ConfigFactory.getCAConnectors(function (data) {
                $scope.CAConnectors = data.result.value;
            });
        };
        $scope.getCAConnectors();

        $scope.delCAConnector = function (connectorname) {
            ConfigFactory.delCAConnector(connectorname, function (data) {
                $scope.getCAConnectors();
            });
        };

        $scope.editCAConnector = function (connectorname, c_type) {
            //debug: console.log(connectorname);
            $state.go("config.caconnectors.edit" + c_type,
                {'connectorname': connectorname});
            $rootScope.returnTo = "config.caconnectors.list";
        };

        // listen to the reload broadcast
        $scope.$on("piReload", $scope.getCAConnectors);
    }]);

myApp.controller("LocalCAConnectorController", ["$scope", "$stateParams",
    "ConfigFactory", "$state",
    function ($scope, $stateParams,
              ConfigFactory, $state) {
        $scope.params = {
            type: 'local'
        };

        $scope.connectorname = $stateParams.connectorname;
        if ($scope.connectorname) {
            /* If we have a connectorname, we do an Edit
             and we need to fill all the $scope.params */
            ConfigFactory.getCAConnector($scope.connectorname, function (data) {
                //debug: console.log(data.result.value);
                var caconnector = data.result.value[0];
                $scope.params = caconnector.data;
                $scope.params.type = 'local';
            });
        }

        $scope.setCAConnector = function () {
            ConfigFactory.setCAConnector($scope.connectorname,
                $scope.params, function (data) {
                    $scope.set_result = data.result.value;
                    $scope.getCAConnectors();
                    $state.go("config.caconnectors.list");
                });
        };

    }]);

myApp.controller("MicrosoftCAConnectorController", ["$scope", "$stateParams",
    "ConfigFactory", "$state",
    function ($scope, $stateParams,
              ConfigFactory, $state) {
        $scope.params = {
            type: 'microsoft'
        };

        $scope.connectorname = $stateParams.connectorname;
        if ($scope.connectorname) {
            /* If we have a connectorname, we do an Edit
             and we need to fill all the $scope.params */
            ConfigFactory.getCAConnector($scope.connectorname, function (data) {
                //debug: console.log(data.result.value);
                var caconnector = data.result.value[0];
                $scope.params = caconnector.data;
                $scope.params.type = 'microsoft';
                $scope.params['type.ssl_client_key_password'] = 'password';
                $scope.getCASpecificOptions($scope.params.type);
            });
        }

        $scope.setCAConnector = function () {
            ConfigFactory.setCAConnector($scope.connectorname,
                $scope.params, function (data) {
                    $scope.set_result = data.result.value;
                    $scope.getCAConnectors();
                    $state.go("config.caconnectors.list");
                });
        };

        $scope.getCASpecificOptions = function (catype) {
            ConfigFactory.getCASpecificOptions(catype,
                $scope.params, function (data) {
                    $scope.available_cas = data.result.value.available_cas;
                });
        }


    }]);

myApp.controller("machineResolverController", ["$scope", "ConfigFactory",
    "$state", "$rootScope",
    "$location",
    function ($scope, ConfigFactory,
              $state, $rootScope,
              $location) {
        if ($location.path() === "/config/machineresolvers") {
            $location.path("/config/machineresolvers/list");
        }

        $scope.getMachineResolvers = function () {
            ConfigFactory.getMachineResolvers(function (data) {
                $scope.machineResolvers = data.result.value;
            });
        };
        $scope.getMachineResolvers();

        $scope.delResolver = function (resolvername) {
            ConfigFactory.delMachineResolver(resolvername, function (data) {
                $scope.getMachineResolvers();
            });
        };

        $scope.editResolver = function (resolvername, r_type) {
            // change the view to the config.mresolvers.edit
            $state.go("config.mresolvers.edit" + r_type, {'resolvername': resolvername});
            $rootScope.returnTo = "config.mresolvers.list";
        };

        // listen to the reload broadcast
        $scope.$on("piReload", $scope.getMachineResolvers);
    }]);

myApp.controller("LdapResolverController", ["$scope", "ConfigFactory", "$state",
    "$stateParams", "inform",
    "gettextCatalog",
    function ($scope, ConfigFactory,
              $state, $stateParams,
              inform, gettextCatalog) {
        /*
         BINDDN, BINDPW, LDAPURI, TIMEOUT, LDAPBASE, LOGINNAMEATTRIBUTE,
         LDAPSEARCHFILTER,
         USERINFO, SIZELIMIT, NOREFERRALS, CACERTIFICATE, AUTHTYPE, EDITABLE
         */
        $scope.authtypes = Object.freeze({
            "Anonymous": "Anonymous",
            "Simple": "Simple",
            "SASL Digest-MD5": "SASL Digest-MD5",
            "NTLM": "NTLM",
            "SASL Kerberos": "SASL Kerberos"
        });
        $scope.params = {
            SIZELIMIT: 500,
            TIMEOUT: 5,
            UIDTYPE: "DN",
            type: 'ldapresolver',
            AUTHTYPE: $scope.authtypes["Simple"],
            SCOPE: "SUBTREE",
            CACHE_TIMEOUT: 120,
            NOSCHEMAS: false,
            TLS_VERIFY: true,
            TLS_VERSION: "2",
            START_TLS: true,
            SERVERPOOL_ROUNDS: 2,
            SERVERPOOL_STRATEGY: "ROUND_ROBIN",
            SERVERPOOL_SKIP: 30
        };
        $scope.result = {};
        $scope.resolvername = $stateParams.resolvername;
        $scope.scopes = ["SUBTREE", "BASE", "LEVEL"];
        $scope.tls_version_options = [{value: "3", name: "TLS v1.0"},
            {value: "4", name: "TLS v1.1"},
            {value: "5", name: "TLS v1.2"},
            {value: "2", name: "TLS v1.3"}];
        $scope.ldap_pooling_strategy_options = ["ROUND_ROBIN", "FIRST", "RANDOM"];

        $('html,body').scrollTop(0);

        if ($scope.resolvername) {
            /* If we have a resolvername, we do an Edit
             and we need to fill all the $scope.params */
            ConfigFactory.getResolver($scope.resolvername, function (data) {
                const resolver = data.result.value[$scope.resolvername];
                //debug: console.log(resolver);
                $scope.params = resolver.data;
                $scope.params.NOREFERRALS = isTrue($scope.params.NOREFERRALS);
                $scope.params.EDITABLE = isTrue($scope.params.EDITABLE);
                $scope.params.TLS_VERIFY = isTrue($scope.params.TLS_VERIFY);
                $scope.params.START_TLS = isTrue($scope.params.START_TLS);
                $scope.params.NOSCHEMAS = isTrue($scope.params.NOSCHEMAS);
                $scope.params.SERVERPOOL_PERSISTENT = isTrue($scope.params.SERVERPOOL_PERSISTENT);
                $scope.params.type = 'ldapresolver';
                $scope.params.recursive_group_search = isTrue($scope.params.recursive_group_search);
            });
        }

        $scope.presetAD = function () {
            $scope.params.LOGINNAMEATTRIBUTE = "sAMAccountName";
            $scope.params.LDAPSEARCHFILTER = "(sAMAccountName=*)(objectCategory=person)";
            $scope.params.USERINFO = '{ "phone" : "telephoneNumber", "mobile" : "mobile", "email" : "mail", "surname" : "sn", "givenname" : "givenName" }';
            $scope.params.NOREFERRALS = true;
            $scope.params.EDITABLE = false;
            $scope.params.UIDTYPE = "objectGUID";
            $scope.params.recursive_group_search = false;
            $scope.params.group_search_filter = "(&(sAMAccountName=*)(objectCategory=group)(member:1.2.840.113556.1.4.1941:=cn={distinguishedName},{base_dn}))";
            $scope.params.group_name_attribute = "distinguishedName";
            $scope.params.group_attribute_mapping_key = "groups";
        };

        $scope.presetLDAP = function () {
            $scope.params.LOGINNAMEATTRIBUTE = "uid";
            $scope.params.LDAPSEARCHFILTER = "(uid=*)(objectClass=inetOrgPerson)";
            $scope.params.USERINFO = '{ "phone" : "telephoneNumber", "mobile" : "mobile", "email" : "mail", "surname" : "sn", "givenname" : "givenName" }';
            $scope.params.NOREFERRALS = true;
            $scope.params.EDITABLE = false;
            $scope.params.UIDTYPE = "entryUUID";
        };

        $scope.setLDAPResolver = function () {
            if (!$scope.params.recursive_group_search) {
                $scope.params.group_name_attribute = "";
                $scope.params.group_search_filter = "";
                $scope.params.group_attribute_mapping_key = "";
            }
            ConfigFactory.setResolver($scope.resolvername, $scope.params, function (data) {
                $scope.set_result = data.result.value;
                $scope.getResolvers();
                $state.go("config.resolvers.list");
            });
        };

        $scope.testResolver = function (size_limit) {
            var params = $.extend({}, $scope.params);
            params["SIZELIMIT"] = size_limit;
            params["resolver"] = $scope.resolvername;
            if (params['AUTHTYPE'] === $scope.authtypes['Anonymous']) {
                params['AUTHTYPE'] = $scope.authtypes['Simple'];
                params['BINDPW'] = '';
                params['BINDDN'] = '';
            }
            ConfigFactory.testResolver(params, function (data) {
                if (data.result.value === true) {
                    inform.add(data.detail.description,
                        {type: "success", ttl: 10000});
                } else {
                    inform.add(data.detail.description,
                        {type: "danger", ttl: 10000});
                }
            });
        };
    }]);

myApp.controller("ScimResolverController", ["$scope", "ConfigFactory", "$state",
    "$stateParams", "inform",
    "gettextCatalog",
    function ($scope, ConfigFactory,
              $state, $stateParams,
              inform, gettextCatalog) {
        /*
         Authserver, Resourceserver, Client, Secret
         */
        $scope.params = {type: "scimresolver"};
        $scope.result = {};
        $scope.resolvername = $stateParams.resolvername;

        if ($scope.resolvername) {
            /* If we have a resolvername, we do an Edit
             and we need to fill all the $scope.params */
            ConfigFactory.getResolver($scope.resolvername, function (data) {
                var resolver = data.result.value[$scope.resolvername];
                //debug: console.log(resolver);
                $scope.params = resolver.data;
                $scope.params.type = 'scimresolver';
            });
        }

        $scope.setSCIMResolver = function () {
            ConfigFactory.setResolver($scope.resolvername, $scope.params, function (data) {
                $scope.set_result = data.result.value;
                $scope.getResolvers();
                $state.go("config.resolvers.list");
            });
        };

        $scope.testResolver = function () {
            ConfigFactory.testResolver($scope.params, function (data) {
                if (data.result.value === true) {
                    inform.add(data.detail.description,
                        {type: "success", ttl: 10000});
                } else {
                    inform.add(data.detail.description,
                        {type: "danger", ttl: 10000});
                }
            });
        };
    }]);

myApp.controller("SqlResolverController", ["$scope", "ConfigFactory", "$state",
    "$stateParams", "inform",
    "gettextCatalog",
    function ($scope, ConfigFactory,
              $state, $stateParams,
              inform, gettextCatalog) {
        $scope.params = {
            type: 'sqlresolver'
        };
        $scope.result = {};
        $scope.resolvername = $stateParams.resolvername;
        $scope.hashtypes = Array("PHPASS", "SHA", "SSHA", "SSHA256", "SSHA512", "OTRS", "SHA512CRYPT", "MD5CRYPT");

        $('html,body').scrollTop(0);

        if ($scope.resolvername) {
            /* If we have a resolvername, we do an Edit
             and we need to fill all the $scope.params */
            ConfigFactory.getResolver($scope.resolvername, function (data) {
                var resolver = data.result.value[$scope.resolvername];
                //debug: console.log(resolver);
                $scope.params = resolver.data;
                $scope.params.type = 'sqlresolver';
                $scope.params.Editable = isTrue($scope.params.Editable);
            });
        }

        $scope.presetWordpress = function () {
            $scope.params.Table = "wp_users";
            $scope.params.Map = '{ "userid" : "ID", "username": "user_login", "email" : "user_email", "givenname" : "display_name", "password" : "user_pass" }';
        };

        $scope.presetOTRS = function () {
            $scope.params.Table = "users";
            $scope.params.Map = '{ "userid" : "id", "username": "login", "givenname" : "first_name", "surname" : "last_name", "password" : "pw" }';
        };

        $scope.presetTine = function () {
            $scope.params.Table = "tine20_accounts";
            $scope.params.Map = '{ "userid" : "id", "username": "login_name", "email" : "email", "givenname" : "first_name", "surname" : "last_name", "password" : "password" }';
        };

        $scope.presetOwncloud = function () {
            $scope.params.Table = "oc_users";
            $scope.params.Map = '{ "userid" : "uid", "username": "uid", "givenname" : "displayname", "password" : "password" }';
        };

        $scope.presetTypo3 = function () {
            $scope.params.Table = "be_users";
            $scope.params.Map = '{ "userid" : "uid", "username": "username", "givenname" : "realName", "password" : "password", "email": "email" }';
        };

        $scope.presetDrupal = function () {
            $scope.params.Table = "user";
            $scope.params.Map = '{"userid": "uid", "username": "name", "email"' +
                ': "mail", "password": "pass" }';
        };

        $scope.setSQLResolver = function () {
            ConfigFactory.setResolver($scope.resolvername, $scope.params, function (data) {
                $scope.set_result = data.result.value;
                $scope.getResolvers();
                $state.go("config.resolvers.list");
            });
        };

        $scope.testSQL = function () {

            var params = $.extend({}, $scope.params);
            params["resolver"] = $scope.resolvername;
            ConfigFactory.testResolver(params, function (data) {
                if (data.result.value >= 0) {
                    inform.add(data.detail.description,
                        {type: "success", ttl: 10000});
                } else {
                    inform.add(data.detail.description,
                        {type: "danger", ttl: 10000});
                }
            });
        };
    }]);

myApp.controller("HTTPResolverController", ["$scope", "ConfigFactory", "$state",
    "$stateParams", "inform", "$location",
    function ($scope, ConfigFactory, $state, $stateParams, inform, $location) {
        $scope.params = {
            type: "httpresolver",
            endpoint: "",
            method: "",
            requestMapping: "",
            responseMapping: "",
            hasSpecialErrorHandler: false,
            headers: "",
            errorResponse: ""
        };

        $scope.typeMapping = {
            "httpresolver": "HTTP Resolver",
            "entraidresolver": "EntraID Resolver",
            "keycloakresolver": "Keycloak Resolver"
        };

        $scope.setTags = function () {
            if ($scope.params.type === "entraidresolver") {
                $scope.endpointTags["checkPass"] = ["{userid}", "{username}", "{password}", "{client_id}",
                    "{client_credential}", "{tenant}"];
            } else {
                $scope.endpointTags["checkPass"] = ["{userid}", "{username}", "{password}"];
            }
            if ($scope.params.type === "keycloakresolver") {
                $scope.endpointTags["createUser"] = ["{username}", "{userid}", "{surname}", "{givenname}",
                    "{email}", "{mobile}", "{phone}"];
                $scope.endpointTags["editUser"] = ["{username}", "{userid}", "{surname}", "{givenname}", "{email}",
                    "{mobile}", "{phone}"];
            } else {
                $scope.endpointTags["createUser"] = ["{username}", "{userid}", "{surname}", "{givenname}",
                    "{email}", "{mobile}", "{phone}", "{password}"];
                $scope.endpointTags["editUser"] = ["{username}", "{userid}", "{surname}", "{givenname}", "{email}",
                    "{mobile}", "{phone}", "{password}"];
            }
        };

        $scope.getDefaultResolverConfig = function () {
            ConfigFactory.getDefaultResolverConfig($scope.params.type, function (data) {
                $scope.setUIParams(data.result.value);
                if ($scope.params.type === "entraidresolver" || $scope.params.type === "keycloakresolver") {
                    // open section with required data to fill
                    $scope.groupIsOpen["authorization"] = true;
                }
                $scope.setTags();
            });
        };

        if ($location.path() === "/config/resolvers/entraidresolver") {
            $scope.params.type = "entraidresolver";
            $scope.getDefaultResolverConfig();
        } else if ($location.path() === "/config/resolvers/keycloakresolver") {
            $scope.params.type = "keycloakresolver";
            $scope.getDefaultResolverConfig();
        }

        $scope.$watch(
            'params.hasSpecialErrorHandler;',
            function (incomingValue) {
                const value = (incomingValue + '').toLowerCase()
                $scope.params.hasSpecialErrorHandler = value === 'true'
            });

        $scope.$watch(
            'params.type;',
            function (newType, oldType) {
                if (newType && oldType !== newType && !$scope.resolvername) {
                    if (newType !== "httpresolver") {
                        $scope.getDefaultResolverConfig();
                    }
                    $scope.setTags();
                    // change the state to select the correct type in the side menu
                    $state.go("config.resolvers.add" + newType);
                }
            });

        $scope.edit = false;
        $scope.resolvername = $stateParams.resolvername;
        if ($scope.resolvername) {
            /* If we have a resolvername, we do an Edit and we need to fill all the $scope.params */
            $scope.edit = true;
            ConfigFactory.getResolver($scope.resolvername, function (data) {
                const resolver = data.result.value[$scope.resolvername];
                resolver.data.type = resolver.type;
                $scope.setUIParams(resolver.data);
                $scope.setTags();
            });
        }

        $scope.setResolver = function () {
            const params = $scope.prepareParamsForServer();
            ConfigFactory.setResolver($scope.resolvername, params, function (
                data
            ) {
                $scope.set_result = data.result.value;
                $scope.getResolvers();
                $state.go("config.resolvers.list");
            });
        };

        $scope.testUser = {"username": "", "userid": ""};
        $scope.testResolver = function () {
            let params = $scope.prepareParamsForServer();
            params["test_username"] = $scope.testUser["username"];
            params["test_userid"] = $scope.testUser["userid"];
            if ($scope.resolvername) {
                params["resolver"] = $scope.resolvername;
            }
            ConfigFactory.testResolver(params, function (data) {
                if (data.result.value === true) {
                    inform.add(data.detail.description, {type: "success", ttl: 10000});
                } else {
                    inform.add(data.detail.description, {type: "danger", ttl: 10000});
                }
            });
        };

        $scope.setUIParams = function (params) {
            if (!angular.isString(params["headers"])) {
                params["headers"] = JSON.stringify(params["headers"]);
            }
            if (params["headers"] && params["headers"] === "{}") {
                params["headers"] = "";
            }

            $scope.advancedSettings = params["advanced"] || false;
            if ($scope.advancedSettings) {
                $scope.params.type = params.type;
                $scope.advancedParams = params;
                $scope.advancedParams["Editable"] = isTrue(params["Editable"]);
                $scope.advancedParams["verify_tls"] = isTrue(params["verify_tls"]);
                $scope.serviceAccount["username"] = params["username"] || "";
                $scope.serviceAccount["password"] = params["password"] || "";
                $scope.updateEndpointConfig("checkPass", params["config_user_auth"]);
                $scope.updateEndpointConfig("userList", params["config_get_user_list"]);
                $scope.updateEndpointConfig("userById", params["config_get_user_by_id"]);
                $scope.updateEndpointConfig("userByName", params["config_get_user_by_name"]);

                $scope.updateEndpointConfig("createUser", params["config_create_user"]);
                $scope.updateEndpointConfig("editUser", params["config_edit_user"]);
                $scope.updateEndpointConfig("deleteUser", params["config_delete_user"]);

                if ($scope.params.type === "entraidresolver") {
                    $scope.authorizationConfig["authority"] = params["authority"];
                    $scope.authorizationConfig["clientId"] = params["client_id"];
                    $scope.authorizationConfig["clientCredentialType"] = params["client_credential_type"];
                    if (params["client_credential_type"] === "certificate") {
                        $scope.authorizationConfig["clientCertificate"] = params["client_certificate"];
                    } else {
                        $scope.authorizationConfig["clientSecret"] = params["client_secret"];
                    }
                    $scope.authorizationConfig["tenant"] = params["tenant"];
                } else if (params["config_authorization"]) {
                    const auth_params = params["config_authorization"];
                    $scope.authorizationConfig = {
                        "method": auth_params["method"],
                        "endpoint": auth_params["endpoint"],
                        "headers": auth_params["headers"],
                        "requestMapping": auth_params["requestMapping"],
                        "responseMapping": auth_params["responseMapping"],
                        "hasSpecialErrorHandler": auth_params["hasSpecialErrorHandler"],
                        "errorResponse": auth_params["errorResponse"]
                    };
                }

                if (params["realm"]) {
                    $scope.advancedParams["realm"] = params["realm"];
                }
            } else {
                $scope.params = params;
            }
        };

        $scope.endpointConfigIsEmpty = function (config) {
            let empty = true;
            angular.forEach(config, function (value, key) {
                if (key !== "method") {
                    if (value && value !== "" && value !== "{}") {
                        empty = false;
                    }
                }
            });
            return empty;
        };

        $scope.prepareParamsForServer = function () {
            let serverParams = {};
            if ($scope.advancedSettings) {
                if ($scope.authorizationConfig["clientCredentialType"] === "certificate") {
                    // checkPass is not supported for EntraID when using certificates
                    delete $scope.advancedParams["config_user_auth"];
                } else {
                    $scope.advancedParams["config_user_auth"] = $scope.endpointConfig["checkPass"];
                }
                $scope.advancedParams["config_get_user_list"] = $scope.endpointConfig["userList"];
                $scope.advancedParams["config_get_user_by_id"] = $scope.endpointConfig["userById"];
                $scope.advancedParams["config_get_user_by_name"] = $scope.endpointConfig["userByName"];
                if ($scope.advancedParams["Editable"]) {
                    $scope.advancedParams["config_create_user"] = $scope.endpointConfig["createUser"];
                    $scope.advancedParams["config_edit_user"] = $scope.endpointConfig["editUser"];
                    $scope.advancedParams["config_delete_user"] = $scope.endpointConfig["deleteUser"];
                }

                // Set authorization config
                if ($scope.advancedParams.type === "entraidresolver") {
                    $scope.advancedParams["client_id"] = $scope.authorizationConfig["clientId"];
                    $scope.advancedParams["client_credential_type"] = $scope.authorizationConfig["clientCredentialType"];
                    if ($scope.advancedParams["client_credential_type"] === "certificate") {
                        $scope.advancedParams["client_certificate"] = $scope.authorizationConfig["clientCertificate"];
                    } else {
                        $scope.advancedParams["client_secret"] = $scope.authorizationConfig["clientSecret"];
                    }
                    $scope.advancedParams["authority"] = $scope.authorizationConfig["authority"];
                    $scope.advancedParams["tenant"] = $scope.authorizationConfig["tenant"];
                } else {
                    $scope.advancedParams["config_authorization"] = $scope.authorizationConfig;
                    $scope.advancedParams["username"] = $scope.serviceAccount["username"];
                    $scope.advancedParams["password"] = $scope.serviceAccount["password"];
                }
                serverParams = $scope.advancedParams;
            } else {
                serverParams = $scope.params;
            }

            // remove undefined entries
            let cleaned_params = {};
            angular.forEach(serverParams, function (value, key) {
                if (value !== undefined && value !== "{}") {
                    cleaned_params[key] = value;
                }
            });
            // Set empty endpoint configs to empty dicts, to indicate that an old config can be removed
            const endpointConfigNames = ["config_get_user_list", "config_get_user_by_id",
                "config_get_user_by_name", "config_user_auth", "config_create_user", "config_edit_user",
                "config_delete_user"];
            angular.forEach(endpointConfigNames, function (configName) {
                if ($scope.endpointConfigIsEmpty(cleaned_params[configName])) {
                    cleaned_params[configName] = {};
                }
            })

            return cleaned_params;
        };

        // ------ ADVANCED SETTINGS ------
        $scope.advancedSettings = false;
        $scope.advancedParams = {
            "advanced": true,
            "type": $scope.params.type,
            "base_url": "",
            "attribute_mapping": {"username": "", "userid": ""},
            "editable": false,
            "verify_tls": true,
            "tls_ca_path": "",
        };

        $scope.authorizationPlaceholders = {
            "endpoint": "https://example.com/auth",
            "headers": '{"Content-Type": "application/json"}',
            "requestMapping": '{"username": "{username}", "password": "{password}"',
            "responseMapping": '{"Authorization": "Bearer {access_token}"}'
        };
        $scope.serviceAccount = {"username": "", "password": ""};

        $scope.toggleAdvancedSettings = function () {
            $scope.advancedSettings = !$scope.advancedSettings;
            $scope.params.type = "httpresolver";
        };

        // Attribute Mapping
        $scope.piAttributes = ["username", "userid", "email", "givenname", "surname", "phone", "mobile"];
        $scope.getRemainingAttributes = function () {
            let remainingAttributes = [];
            angular.forEach($scope.piAttributes, function (attribute) {
                if (!$scope.advancedParams.attribute_mapping.hasOwnProperty(attribute)) {
                    remainingAttributes.push(attribute);
                }
            });
            return remainingAttributes;
        };

        $scope.addAttribute = function (attribute) {
            if (attribute && $scope.piAttributes.indexOf(attribute) > -1) {
                $scope.advancedParams.attribute_mapping[attribute] = "";
            }
        };

        $scope.removeAttribute = function (attribute) {
            if (attribute && $scope.advancedParams.attribute_mapping.hasOwnProperty(attribute)) {
                delete $scope.advancedParams.attribute_mapping[attribute];
            }
        };

        $scope.serializedDictParams = ["headers", "requestMapping", "responseMapping", "errorResponse"];
        $scope.updateEndpointConfig = function (endpointName, newConfig) {
            // serializes the dicts of the endpoint configs for a simplified display
            // TODO: Maybe change this to a more userfriendly display in the new WebUI
            if (newConfig) {
                angular.forEach($scope.serializedDictParams, function (param) {
                    if (newConfig[param] && !angular.isString(newConfig[param])) {
                        if (!angular.isString(newConfig[param])) {
                            newConfig[param] = JSON.stringify(newConfig[param]);
                        }
                        // Do not display empty dicts
                        newConfig[param] = newConfig[param].replace("{}", "")
                    }
                });
                $scope.endpointConfig[endpointName] = newConfig;
            }
        }

        $scope.$watch('advancedParams.Editable;',
            function (newValue, oldValue) {
                if (newValue === true) {
                    $scope.userEndpointNames = {
                        "checkPass": "Check User Password",
                        "userList": "User List",
                        "userById": "Get User by ID",
                        "userByName": "Get User by Name",
                        "createUser": "Create User",
                        "editUser": "Edit User",
                        "deleteUser": "Delete User"
                    };
                    if (!$scope.edit) {
                        $scope.groupIsOpen["createUser"] = true;
                    }
                } else {
                    $scope.userEndpointNames = {
                        "checkPass": "Check User Password",
                        "userList": "User List",
                        "userById": "Get User by ID",
                        "userByName": "Get User by Name"
                    };
                }
            });

        // Detailed Endpoint Configuration
        $scope.initDetailedEndpointConfig = function () {
            $scope.userEndpointNames = {
                "checkPass": "Check User Password",
                "userList": "User List",
                "userById": "Get User by ID",
                "userByName": "Get User by Name",
                "createUser": "Create User",
                "editUser": "Edit User",
                "deleteUser": "Delete User"
            };
            $scope.groupIsOpen = {"authorization": false};
            $scope.endpointConfig = {};
            $scope.authorizationConfig = {};
            $scope.endpointPlaceholders = {};
            $scope.endpointTags = {
                "checkPass": ["{userid}", "{username}", "{password}"],
                "userById": ["{userid}"], "userByName": ["{username}"],
                "userList": ["{username}", "{userid}", "{surname}", "{givenname}"],
                "createUser": ["{username}", "{userid}", "{surname}", "{givenname}", "{email}", "{mobile}", "{phone}",
                    "{password}"],
                "editUser": ["{username}", "{userid}", "{surname}", "{givenname}", "{email}", "{mobile}", "{phone}",
                    "{password}"],
                "deleteUser": ["{userid}"]
            };
            angular.forEach($scope.userEndpointNames, function (value, key) {
                $scope.endpointConfig[key] = {};
                $scope.groupIsOpen[key] = false;
                $scope.endpointPlaceholders[key] = {
                    "headers": '{"Content-Type": "application/json; charset=UTF-8"}',
                    "requestMapping": '{"customerid": "{userid}", "accessKey": "secr3t!"}',
                    "responseMapping": '{"username": "{Username}", "email": "{Email}"}',
                    "errorResponse": '{"success": false, "message": "An error occurred!"}'
                };
            });
            $scope.endpointPlaceholders["checkPass"]["endpoint"] = "/openid-connect/token";
            $scope.endpointPlaceholders["userList"]["endpoint"] = "/users";
            $scope.endpointPlaceholders["userById"]["endpoint"] = "/users/{userid}";
            $scope.endpointPlaceholders["userByName"]["endpoint"] = "/users/{username}";
            $scope.endpointPlaceholders["createUser"]["endpoint"] = "/users";
            $scope.endpointPlaceholders["editUser"]["endpoint"] = "/users/{userid}";
            $scope.endpointPlaceholders["deleteUser"]["endpoint"] = "/users/{userid}";

            // Authorization Config
        };
        $scope.initDetailedEndpointConfig();
    }]);
