/**
 * http://www.privacyidea.org
 *
 * 2020-05-14 Cornelius Kölbel, <cornelius.koelbel@netknights.it>
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


myApp.controller("dashboardController", ["ConfigFactory", "TokenFactory",
                                         "SubscriptionFactory", "AuditFactory",
                                         "$scope", "$location", "AuthFactory", "$timeout",
                                         "InfoFactory", "inform",
                                         function (ConfigFactory, TokenFactory,
                                                   SubscriptionFactory, AuditFactory,
                                                   $scope, $location, AuthFactory, $timeout,
                                                   InfoFactory, inform) {

    $scope.tokens = {"total": 0, "hardware": 0};
    $scope.certificates = {"entries": [], "summary": {"ok": 0, "warning": 0,
                                                      "critical": 0, "expired": 0,
                                                      "error": 0, "not_configured": 0},
                           "loading": false};
    $scope.resolverTiming = {"entries": [], "loading": false, "since_seconds": 3600};
    $scope.notificationDelivery = {"push": [], "sms": [], "email": [],
                                   "loading": false, "since_seconds": 3600,
                                   "totals": {"push": 0, "sms": 0, "email": 0}};
    // Lookup populated alongside the notification delivery panel so push/sms
    // target names can link to their gateway edit page (the route needs id).
    $scope.smsGatewayIdByName = {};
    $scope.policies = {"active": [], "num_active": 0,
                       "inactive": [], "num_inactive": 0};
    $scope.events = {"active": [], "num_active": 0,
                     "inactive": [], "num_inactive": 0};
    // Flat, sectioned rows for the subscription overview (see buildSubscriptionRows).
    $scope.subscriptionRows = [];
    // null = still loading, "ok" = loaded, "error" = request failed
    $scope.pluginStatusLoadState = null;
    // The overview has two independent axes, each rendered as a coloured dot.
    // The maps below give the bootstrap text-color class and the label per
    // value. `gettext()` is the angular-gettext no-op marker so the extractor
    // picks the strings up; the template applies the `translate` filter so the
    // rendered label reacts to language changes.
    // Usage: is the plugin actively used / covered?
    $scope.usageDot = {
        "yes": "text-success",   // green
        "no": "text-danger"      // red
    };
    $scope.usageText = {
        "yes": gettext("Yes"),
        "no": gettext("No")
    };
    // Subscription: state of the subscription record itself.
    $scope.subscriptionDot = {
        "none": "text-muted",      // grey
        "valid": "text-success",   // green
        "expiring": "text-warning",// yellow
        "exceeded": "text-warning",// yellow
        "expired": "text-danger"   // red
    };
    $scope.subscriptionText = {
        "none": gettext("None"),
        "valid": gettext("Valid"),
        "expiring": gettext("Expiring"),
        "exceeded": gettext("Exceeded"),
        "expired": gettext("Expired")
    };
    // Tooltip explaining the concrete reason for a dot's colour. For the usage
    // "OR" rule we state which branch actually applies (subscription vs. recent
    // activity), rather than making the admin guess. Returned strings are the
    // gettext() source; the template applies the `translate` filter.
    $scope.usageReasonText = function (status) {
        if (status.usage === "yes") {
            return status.subscription !== "none"
                ? gettext("In use: covered by a subscription.")
                : gettext("In use: seen within the last 7 days.");
        }
        return gettext("Not in use: no subscription, and not seen in the last 7 days.");
    };
    $scope.subscriptionReasonText = function (status) {
        return {
            "none": gettext("No subscription. Get a subscription for enterprise support."),
            "valid": gettext("Valid: subscription in place and no other condition applies."),
            "expiring": gettext("Expiring: the subscription ends in less than 60 days."),
            "exceeded": gettext("Exceeded: subscription is valid, but more tokens are in use than it allows."),
            "expired": gettext("Expired: the subscription's end date has passed.")
        }[status.subscription] || "";
    };
    // Display name per plugin application key. The privacyidea- prefix is
    // dropped — context already makes it obvious. Unknown keys fall back to
    // the raw application identifier in the view.
    $scope.pluginDisplayName = {
        "privacyidea": "privacyIDEA Server",
        "privacyidea-app": "privacyIDEA Authenticator App",
        "privacyidea-radius": "RADIUS",
        "privacyidea-cp": "Windows Credential Provider",
        "privacyidea-pam": "PAM OTP & Push",
        "pam-passkey": "PAM Passkey",
        "privacyidea-keycloak": "Keycloak",
        "entraid-via-keycloak": "EntraID Integration",
        "privacyidea-adfs": "AD FS",
        "privacyidea-shibboleth": "Shibboleth"
    };
    // External link target per component, split by subscription state:
    //   sub   -> shown when a subscription exists
    //   nosub -> shown when there is no subscription
    // TODO: replace the placeholders with the real per-component URLs. Targets
    // must stay on a host allowed by the href sanitization list in app.js.
    var LINK_SUB = "https://netknights.it/";
    var LINK_NOSUB = "https://privacyidea.org/";
    $scope.componentLinks = {
        "privacyidea":            {sub: LINK_SUB, nosub: LINK_NOSUB},
        "privacyidea-app":        {sub: LINK_SUB, nosub: LINK_NOSUB},
        "privacyidea-radius":     {sub: LINK_SUB, nosub: LINK_NOSUB},
        "privacyidea-cp":         {sub: LINK_SUB, nosub: LINK_NOSUB},
        "privacyidea-pam":        {sub: LINK_SUB, nosub: LINK_NOSUB},
        "pam-passkey":            {sub: LINK_SUB, nosub: LINK_NOSUB},
        "privacyidea-keycloak":   {sub: LINK_SUB, nosub: LINK_NOSUB},
        "entraid-via-keycloak":   {sub: LINK_SUB, nosub: LINK_NOSUB},
        "privacyidea-adfs":       {sub: LINK_SUB, nosub: LINK_NOSUB},
        "privacyidea-shibboleth": {sub: LINK_SUB, nosub: LINK_NOSUB}
    };
    // Pick the link for a row based on whether it has a subscription. Returns
    // "" when the component has no configured link (then it renders as text).
    $scope.componentLinkTarget = function (status) {
        var links = $scope.componentLinks[status.application];
        if (!links) { return ""; }
        return status.subscription === "none" ? links.nosub : links.sub;
    };
    // Subscription overview view mode. Start compact; the "Show details" button
    // switches to the detailed view (adds the Expires and Last seen columns).
    $scope.subscriptionDetailed = false;
    $scope.toggleSubscriptionDetail = function () {
        $scope.subscriptionDetailed = !$scope.subscriptionDetailed;
    };
    // Copy the panel's data (server + component rows, without the section
    // labels) as a JSON string to the clipboard.
    $scope.copySubscriptionInfo = function () {
        // Normalize the timestamp fields to ISO 8601 so the copied JSON is
        // uniform (last_seen arrives as an RFC-1123 string, date_till as a
        // Date). Copy each status so the displayed rows are not mutated.
        var toIso = function (value) {
            if (!value) { return value; }
            var date = (value instanceof Date) ? value : new Date(value);
            return isNaN(date.getTime()) ? value : date.toISOString();
        };
        var data = $scope.subscriptionRows
            .filter(function (row) { return row.kind !== "label"; })
            .map(function (row) {
                return angular.extend({}, row.status, {
                    last_seen: toIso(row.status.last_seen),
                    date_till: toIso(row.status.date_till)
                });
            });
        var json = JSON.stringify(data, null, 2);
        var ok = function () {
            inform.add(gettext("Subscription info copied to clipboard."),
                       {type: "info", ttl: 3000});
        };
        var fail = function () {
            inform.add(gettext("Could not copy to the clipboard."),
                       {type: "danger", ttl: 5000});
        };
        if (navigator.clipboard && navigator.clipboard.writeText) {
            navigator.clipboard.writeText(json).then(ok, fail);
        } else {
            // Fallback for non-secure contexts where navigator.clipboard is absent.
            try {
                var textarea = document.createElement("textarea");
                textarea.value = json;
                document.body.appendChild(textarea);
                textarea.select();
                document.execCommand("copy");
                document.body.removeChild(textarea);
                ok();
            } catch (e) {
                fail();
            }
        }
    };
    $scope.authentications = {"success": 0, "fail": 0};
    $scope.latestNews = null;

    $scope.getLatestNews = function () {
        InfoFactory.getRSS(function (rss) {
            // rss is { source: [items, ...], ... }; pick the first item of the
            // first source - matches what the news page shows at the top.
            for (var source in rss) {
                if (rss.hasOwnProperty(source) && rss[source] && rss[source].length) {
                    var item = rss[source][0];
                    // RFC-822 pub_date string -> Date so the date filter works.
                    if (item.pub_date) item.pub_date = new Date(item.pub_date);
                    $scope.latestNews = item;
                    return;
                }
            }
            $scope.latestNews = null;
        });
    };

    $scope.get_total_token_number = function () {
        // We call getTokens with pagesize=0, so that we do
        // not need any user resolving.
        TokenFactory.getTokensNoCancel(function (data) {
                if (data) {
                    $scope.tokens.total = data.result.value.count;
                }
            }, {"pagesize": 0});
    };

    $scope.get_token_hardware = function () {
        TokenFactory.getTokensNoCancel(function (data) {
                if (data) {
                    $scope.tokens.hardware = data.result.value.count;
                }
            }, {"pagesize": 0, "infokey": "tokenkind", "infovalue": "hardware"});
        TokenFactory.getTokensNoCancel(function (data) {
            if (data) {
                $scope.tokens.unassigned_hardware = data.result.value.count;
            }
        }, {"pagesize": 0, "infokey": "tokenkind", "infovalue": "hardware", "assigned": "False"});
    };

    $scope.get_token_software = function () {
        TokenFactory.getTokensNoCancel(function (data) {
                if (data) {
                    $scope.tokens.software = data.result.value.count;
                }
            }, {"pagesize": 0, "infokey": "tokenkind", "infovalue": "software"});
        TokenFactory.getTokensNoCancel(function (data) {
            if (data) {
                $scope.tokens.unassigned_software = data.result.value.count;
            }
        }, {"pagesize": 0, "infokey": "tokenkind", "infovalue": "software", "assigned": "False"});
    };

    $scope.get_policies = function () {
        ConfigFactory.getPolicies(function(data) {
            $scope.policies = {"active": [], "num_active": 0,
                       "inactive": [], "num_inactive": 0};
            var policies = data.result.value;
            angular.forEach(policies, function(policy) {
                if (policy.active) {
                    $scope.policies.active.push(policy.name);
                    $scope.policies.num_active += 1;
                } else {
                    $scope.policies.inactive.push(policy.name);
                    $scope.policies.num_inactive += 1;
                }
            });
        });
    };

    $scope.get_events = function () {
        $scope.events = {"active": [], "num_active": 0,
                     "inactive": [], "num_inactive": 0};
        ConfigFactory.getEvents(function(data) {
            var events = data.result.value;
            angular.forEach(events, function(event) {
                if (event.active) {
                    $scope.events.active.push(event);
                    $scope.events.num_active += 1;
                } else {
                    $scope.events.inactive.push(event);
                    $scope.events.num_inactive += 1;
                }
            });
        });
    };


     // Hierarchy of the subscription overview. The server is the base component
     // and is rendered on its own at the top. Everything else is a "use case",
     // some grouped under sub-labels. Labels are pure headers; plugin nodes pull
     // their status from the backend by `application`. This tree is flattened
     // into rows with an `indent` level for rendering (see buildSubscriptionRows).
     var SUBSCRIPTION_SECTIONS = [
         {kind: "label", label: gettext("Use Cases"), children: [
             {kind: "plugin", application: "privacyidea-app"},
             {kind: "plugin", application: "privacyidea-radius"},
             {kind: "label", label: gettext("System Login"), children: [
                 {kind: "plugin", application: "privacyidea-cp"},
                 {kind: "plugin", application: "privacyidea-pam"},
                 {kind: "plugin", application: "pam-passkey"}
             ]},
             {kind: "label", label: gettext("Single Sign On"), children: [
                 {kind: "plugin", application: "privacyidea-keycloak"},
                 {kind: "plugin", application: "entraid-via-keycloak"},
                 {kind: "plugin", application: "privacyidea-adfs"},
                 {kind: "plugin", application: "privacyidea-shibboleth"}
             ]}
         ]}
     ];

     // Default status for a section plugin the backend did not report (e.g.
     // RADIUS, which has no subscription application yet).
     function unusedStatus(application) {
         return {application: application, usage: "no", subscription: "none",
                 date_till: null, days_left: null, last_seen: null,
                 versions: [], current_version: null,
                 current_version_date: null, current_version_url: null};
     }

     function flattenSections(nodes, depth, rows, statusByApp) {
         nodes.forEach(function (node) {
             if (node.kind === "label") {
                 rows.push({kind: "label", label: node.label, indent: depth});
                 flattenSections(node.children || [], depth + 1, rows, statusByApp);
             } else {
                 rows.push({kind: "plugin", indent: depth, application: node.application,
                            status: statusByApp[node.application] || unusedStatus(node.application)});
             }
         });
         return rows;
     }

     // Turn the backend status list into the flat, sectioned row list the
     // template renders: server row first, then the flattened use-case tree.
     function buildSubscriptionRows(entries) {
         var statusByApp = {};
         var serverEntry = null;
         (entries || []).forEach(function (entry) {
             // date_till arrives as an RFC-1123 string; parse it to a Date so
             // the `date` filter can format it (otherwise it renders verbatim
             // with the time and timezone).
             if (entry.date_till) { entry.date_till = new Date(entry.date_till); }
             if (entry.is_server) { serverEntry = entry; }
             statusByApp[entry.application] = entry;
         });
         var rows = [{kind: "server", indent: 0,
                      status: serverEntry || unusedStatus("privacyidea")}];
         return flattenSections(SUBSCRIPTION_SECTIONS, 0, rows, statusByApp);
     }

     $scope.getPluginStatus = function() {
        $scope.pluginStatusLoadState = null;
        SubscriptionFactory.getStatus(function (data) {
            $scope.subscriptionRows = buildSubscriptionRows(data.result.value);
            $scope.pluginStatusLoadState = "ok";
        }, function () {
            $scope.subscriptionRows = [];
            $scope.pluginStatusLoadState = "error";
        });
     };

$scope.getAuthentication = function () {
  $scope.authentications = {"success": 0, "fail": 0};
  AuditFactory.get({"timelimit": "1d", "action": "*validate*", "success": "1"},
      function (data) {
          $scope.authentications.success = data.result.value.count;
      });
  AuditFactory.get({"timelimit": "1d", "action": "*validate*", "success": "0"},
      function (data) {
          $scope.authentications.fail = data.result.value.count;
          $scope.authentications.users = {}; // Declare the users object as a dictionary
          $scope.authentications.serials = Array();
          angular.forEach(data.result.value.auditdata, function(auditentry){
              if (auditentry.user) {
                  // Check if the user already exists in the dictionary
                  if (!$scope.authentications.users[auditentry.user + "-" + auditentry.realm]) {
                      // Add the user to the dictionary with a count of 1 and the latest error date
                      $scope.authentications.users[auditentry.user + "-" + auditentry.realm] = {"user": auditentry.user, "realm": auditentry.realm, "fails": 1, "latestError": auditentry.date};
                  } else {
                      // Increment the number of fails for the existing user and update the latest error date
                      $scope.authentications.users[auditentry.user + "-" + auditentry.realm].fails++;
                      if (auditentry.date > $scope.authentications.users[auditentry.user + "-" + auditentry.realm].latestError) {
                          $scope.authentications.users[auditentry.user + "-" + auditentry.realm].latestError = auditentry.date;
                      }
                  }
              } else {
                  $scope.authentications.serials.push(auditentry.serial);
              }
          });
          // Convert the dictionary to an array and sort it by the latest error date
          $scope.authentications.users = Object.values($scope.authentications.users);
          $scope.authentications.users.sort(function(a, b) {
                return b.latestError - a.latestError;
          });
      });
};

     $scope.getAdministration = function () {
         $scope.administration = [];
         angular.forEach(["system", "resolver", "realm", "policy", "event"],
             function(adminaction) {
                AuditFactory.get({"timelimit": "1d", "action": "POST /"+adminaction+"*"},
                    function (data) {
                    angular.forEach(data.result.value.auditdata, function(auditentry) {
                        $scope.administration.push(auditentry);
                    });
                    // reverse sort it by date
                    $scope.administration.sort($scope.compare_auditentries);
                    // only return the last 5 entries
                    $scope.administration = $scope.administration.slice(0, 5);
                });
             });
     };

     $scope.getCertificateHealth = function (refresh) {
         $scope.certificates.loading = true;
         ConfigFactory.getCertificateHealth(refresh, function (data) {
             var entries = (data && data.result && data.result.value) || [];
             var summary = {"ok": 0, "warning": 0, "critical": 0,
                            "expired": 0, "error": 0, "not_configured": 0};
             angular.forEach(entries, function (e) {
                 if (summary[e.status] !== undefined) {
                     summary[e.status] += 1;
                 }
             });
             // Sort: most urgent first, then by days remaining ascending.
             var order = {"expired": 0, "critical": 1, "error": 2, "warning": 3,
                          "not_configured": 4, "ok": 5};
             entries.sort(function (a, b) {
                 var oa = order[a.status] !== undefined ? order[a.status] : 99;
                 var ob = order[b.status] !== undefined ? order[b.status] : 99;
                 if (oa !== ob) return oa - ob;
                 var da = a.days_remaining === null ? Infinity : a.days_remaining;
                 var db = b.days_remaining === null ? Infinity : b.days_remaining;
                 return da - db;
             });
             $scope.certificates.entries = entries;
             $scope.certificates.summary = summary;
             $scope.certificates.loading = false;
         }, function () {
             $scope.certificates.loading = false;
         });
     };

     // p95 latency thresholds (seconds) for the resolver timing panel.
     // Below LATENCY_OK_S: green; below LATENCY_WARN_S: yellow; above: red.
     var LATENCY_OK_S = 0.1;
     var LATENCY_WARN_S = 0.5;

     // Approximate a quantile from cumulative histogram buckets, mirroring the
     // server's privacyidea.lib.metrics._percentile_from_buckets: return the
     // upper bound of the first bucket whose cumulative count crosses q*count.
     // Returns null for an empty histogram or when the quantile sits in the
     // open-ended (> largest bucket) tail.
     function combinedPercentile(bounds, sums, count, q) {
         if (!count || !bounds || !bounds.length) return null;
         var target = q * count;
         for (var i = 0; i < bounds.length; i++) {
             if ((sums[i] || 0) >= target) return bounds[i];
         }
         return null;
     }

     // Map resolver_type -> ui-router state for the resolver detail link.
     var RESOLVER_DETAIL_STATE = {
         "ldapresolver": "config.resolvers.editldapresolver",
         "sqlresolver": "config.resolvers.editsqlresolver",
         "httpresolver": "config.resolvers.edithttpresolver",
         "entraidresolver": "config.resolvers.editentraidresolver",
         "keycloakresolver": "config.resolvers.editkeycloakresolver",
         "passwdresolver": "config.resolvers.editpasswdresolver"
     };

     $scope.getResolverTiming = function () {
         $scope.resolverTiming.loading = true;
         ConfigFactory.getResolverTiming($scope.resolverTiming.since_seconds, function (data) {
             var raw = (data && data.result && data.result.value) || [];
             // Group by (resolver, resolver_type): roll up per-op rows into a
             // per-resolver total plus a by_op breakdown.
             var byKey = {};
             angular.forEach(raw, function (e) {
                 var resolver = (e.labels && e.labels.resolver) || "?";
                 var type = (e.labels && e.labels.resolver_type) || "?";
                 var op = (e.labels && e.labels.op) || "?";
                 var key = type + "|" + resolver;
                 if (!byKey[key]) {
                     byKey[key] = {
                         "resolver": resolver,
                         "resolver_type": type,
                         "detail_state": RESOLVER_DETAIL_STATE[type] || null,
                         "count": 0,
                         "max": 0,
                         "bucket_bounds": [],    // upper bounds (seconds), from the server
                         "bucket_sums": [],      // cumulative counts summed across ops
                         "avg_weighted_sum": 0,  // sum(avg * count) for weighted avg
                         "by_op": []
                     };
                 }
                 var r = byKey[key];
                 r.count += e.count || 0;
                 if (e.max !== null && e.max > r.max) r.max = e.max;
                 // Sum the per-op histograms element-wise. Every row uses the same
                 // ordered bucket boundaries, so a correct resolver-level p95 comes
                 // from the combined histogram - not from max() of the per-op p95s,
                 // which overstates it when one low-traffic op has a slow outlier.
                 var b = e.buckets || [];
                 if (!r.bucket_bounds.length) {
                     r.bucket_bounds = b.map(function (p) { return p[0]; });
                     r.bucket_sums = b.map(function (p) { return p[1] || 0; });
                 } else {
                     for (var i = 0; i < b.length; i++) {
                         r.bucket_sums[i] = (r.bucket_sums[i] || 0) + (b[i][1] || 0);
                     }
                 }
                 if (e.avg !== null) r.avg_weighted_sum += e.avg * (e.count || 0);
                 r.by_op.push({"op": op, "count": e.count, "avg": e.avg,
                               "p50": e.p50, "p95": e.p95, "max": e.max});
             });
             var entries = [];
             angular.forEach(byKey, function (r) {
                 r.avg = r.count > 0 ? (r.avg_weighted_sum / r.count) : null;
                 r.p95 = combinedPercentile(r.bucket_bounds, r.bucket_sums, r.count, 0.95);
                 entries.push(r);
             });
             // Sort: highest p95 first, then by count desc.
             entries.sort(function (a, b) {
                 var ap = a.p95 === null ? -1 : a.p95;
                 var bp = b.p95 === null ? -1 : b.p95;
                 if (ap !== bp) return bp - ap;
                 return b.count - a.count;
             });
             $scope.resolverTiming.entries = entries;
             $scope.resolverTiming.loading = false;
         }, function () {
             $scope.resolverTiming.loading = false;
         });
     };

     $scope.getNotificationDelivery = function () {
         $scope.notificationDelivery.loading = true;
         ConfigFactory.getNotificationDelivery($scope.notificationDelivery.since_seconds, function (data) {
             var v = (data && data.result && data.result.value) || {};
             ["push", "sms", "email"].forEach(function (channel) {
                 var entries = v[channel] || [];
                 var total = 0;
                 entries.forEach(function (e) { total += e.total || 0; });
                 $scope.notificationDelivery[channel] = entries;
                 $scope.notificationDelivery.totals[channel] = total;
             });
             $scope.notificationDelivery.loading = false;
         }, function () {
             $scope.notificationDelivery.loading = false;
         });
         ConfigFactory.getSMSGateways(null, function (data) {
             var gateways = (data && data.result && data.result.value) || [];
             var map = {};
             angular.forEach(gateways, function (gw) {
                 if (gw && gw.name) map[gw.name] = gw.id;
             });
             $scope.smsGatewayIdByName = map;
         });
     };

     // Failure-rate color: green <1%, yellow <5%, red >=5%. No data => muted.
     $scope.deliveryFailureClass = function (entry) {
         if (!entry || !entry.total) return "text-muted";
         var failed = (entry.failed || 0) + (entry.error || 0);
         var rate = failed / entry.total;
         if (rate < 0.01) return "text-success";
         if (rate < 0.05) return "text-warning";
         return "text-danger";
     };

     // Short label shown next to the resolver name (e.g. "ldap", "sql").
     $scope.resolverTypeLabel = function (resolverType) {
         if (!resolverType) return "";
         return resolverType.replace(/resolver$/, "");
     };

     $scope.resolverLatencyClass = function (seconds) {
         if (seconds === null || seconds === undefined) return "text-muted";
         if (seconds < LATENCY_OK_S) return "text-success";
         if (seconds < LATENCY_WARN_S) return "text-warning";
         return "text-danger";
     };

     // Render a duration in the most readable unit.
     $scope.formatDuration = function (seconds) {
         if (seconds === null || seconds === undefined) return "-";
         if (seconds < 1) return Math.round(seconds * 1000) + " ms";
         return seconds.toFixed(2) + " s";
     };

     $scope.certificateTextClass = function (status) {
         return {"expired": "text-danger", "critical": "text-danger",
                 "warning": "text-warning", "error": "text-warning",
                 "not_configured": "text-muted", "ok": "text-success"}[status] || "";
     };

     $scope.certificateStatusIcon = function (status) {
         // Returns a map of glyphicon class + bootstrap text color for the status icon.
         var icon = {"expired": "glyphicon-exclamation-sign",
                     "critical": "glyphicon-exclamation-sign",
                     "warning": "glyphicon-warning-sign",
                     "error": "glyphicon-warning-sign",
                     "not_configured": "glyphicon-minus-sign",
                     "ok": "glyphicon-ok-sign"}[status] || "glyphicon-question-sign";
         var color = $scope.certificateTextClass(status);
         var classes = {};
         classes[icon] = true;
         if (color) classes[color] = true;
         return classes;
     };

     $scope.compare_auditentries = function (a, b) {
        if (a.date < b.date ) return 1;
        if (b.date < a.date ) return -1;
        return 0;
     };

    if (AuthFactory.checkRight('tokenlist')) {
        $scope.get_total_token_number();
        $scope.get_token_hardware();
        $scope.get_token_software();
    }
    if (AuthFactory.checkRight('policyread')) {
        $scope.get_policies();
    }
    if (AuthFactory.checkRight('eventhandling_read')) {
        $scope.get_events();
    }
    if (AuthFactory.checkRight('managesubscription')) {
        $scope.getPluginStatus();
    }
    if (AuthFactory.checkRight('auditlog')) {
        $scope.getAuthentication();
        $scope.getAdministration();
    }
    if (AuthFactory.checkRight('configread')) {
        $scope.getCertificateHealth(false);
        $scope.getResolverTiming();
        $scope.getNotificationDelivery();
    }
    $scope.getLatestNews();

        // listen to the reload broadcast
    $scope.$on("piReload", function() {
        if (AuthFactory.checkRight('tokenlist')) {
            $scope.get_total_token_number();
            $scope.get_token_hardware();
            $scope.get_token_software();
        }
        if (AuthFactory.checkRight('policyread')) {
            $scope.get_policies();
        }
        if (AuthFactory.checkRight('eventhandling_read')) {
            $scope.get_events();
        }
        if (AuthFactory.checkRight('managesubscription')) {
            $scope.getPluginStatus();
        }
        if (AuthFactory.checkRight('auditlog')) {
            $scope.getAuthentication();
            $scope.getAdministration();
        }
        if (AuthFactory.checkRight('configread')) {
            $scope.getCertificateHealth(false);
            $scope.getResolverTiming();
            $scope.getNotificationDelivery();
            // The other panels' init calls may indirectly trigger resolver
            // operations that won't have committed by the time the first
            // timing fetch returns. Re-fetch shortly after to catch anything
            // recorded during the init storm.
            $timeout(function () { $scope.getResolverTiming(); }, 1500);
        }
        $scope.getLatestNews();
    });
}]);
