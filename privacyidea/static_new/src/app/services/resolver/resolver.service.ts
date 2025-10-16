import { httpResource } from "@angular/common/http";
import { environment } from "../../../environments/environment";
import { PiResponse } from "../../app.component";
import { AuthService } from "../auth/auth.service";
import { computed, effect, inject, Injectable, signal } from "@angular/core";

type ResolverType = "ldapresolver" | "sqlresolver" | "passwdresolver" | "scimresolver";

export interface ResolverData {}

/*
Resolvers changed:
  deflocal: Object { censor_keys: [], resolvername: "deflocal", type: "passwdresolver", … }
  censor_keys: Array []
  data: Object { filename: "/etc/passwd" }
    filename: "/etc/passwd"
  resolvername: "deflocal"
  type: "passwdresolver"
  */

export type Resolvers = { [key: string]: Resolver };

export interface Resolver {
  censor_keys: string[];
  data: ResolverData;
  resolvername: string;
  type: ResolverType;
}

export interface LDAPResolverData extends ResolverData {
  ldapuri: string;
  ldapbase: string;
  authtype: string;
  binddn: string;
  bindpw: string;
  timeout: number;
  cache_timeout: number;
  sizelimit: number;
  loginnameattribute: string;
  ldapsearchfilter: string;
  ldapfilter: string;
  multivalueattributes: string;
  userinfo: string;
  uidtype: string;
  noreferrals: boolean;
  noschemas: boolean;
  editable: boolean;
  start_tls: boolean;
  tls_verify: boolean;
  tls_version: string;
}

export interface SQLResolverDara extends ResolverData {
  database: string;
  driver: string;
  server: string;
  port: number;
  user: string;
  password: string;
  table: string;
  map: string;
}

export interface PasswdResolverData extends ResolverData {
  filename: string;
}

export interface SCIMResolverData extends ResolverData {
  scimurl: string;
  user: string;
  password: string;
  verifyssl: boolean;
  timeout: number;
  cache_timeout: number;
  loginnameattribute: string;
  userinfo: string;
  editable: boolean;
}

/*
The code of this module is tested in tests/test_api_system.py
POST /resolver/test
    Send the complete parameters of a resolver to the privacyIDEA server to test, if these settings will result in a successful connection. If you are testing existing resolvers, you can send the “__CENSORED__” password. privacyIDEA will use the already stored password from the database.
    Return
        a json result with True, if the given values can create a working resolver and a description.
GET /resolver/(resolver)
GET /resolver/
    returns a json list of the specified resolvers. The passwords of resolvers (e.g. Bind PW of the LDAP resolver or password of the SQL resolver) will be returned as “__CENSORED__”. You can run a POST request to update the data and privacyIDEA will ignore the “__CENSORED__” password or you can even run a testresolver.
    Parameters
            resolver (str) – the name of the resolver
            type (str) – Only return resolvers of type (like passwdresolver..)
            editable (str) – Set to “1” if only editable resolvers should be returned.
    Return
        a json result with the configuration of resolvers
POST /resolver/(resolver)
    This creates a new resolver or updates an existing one. A resolver is uniquely identified by its name.
    If you update a resolver, you do not need to provide all parameters. Parameters you do not provide are left untouched. When updating a resolver you must not change the type! You do not need to specify the type, but if you specify a wrong type, it will produce an error.
    Parameters
            resolver (str) – the name of the resolver.
            type – the type of the resolver. Valid types are passwdresolver,
    ldapresolver, sqlresolver, scimresolver :type type: str :return: a json result with the value being the database id (>0)
    Additional parameters depend on the resolver type.
        LDAP:
                LDAPURI
                LDAPBASE
                AUTHTYPE
                BINDDN
                BINDPW
                TIMEOUT
                CACHE_TIMEOUT
                SIZELIMIT
                LOGINNAMEATTRIBUTE
                LDAPSEARCHFILTER
                LDAPFILTER
                LOGINNAMEATTRIBUTE
                MULTIVALUEATTRIBUTES
                USERINFO
                UIDTYPE
                NOREFERRALS - True|False
                NOSCHEMAS - True|False
                EDITABLE - True|False
                START_TLS - True|False
                TLS_VERIFY - True|False
                TLS_VERSION
        SQL:
                Database
                Driver
                Server
                Port
                User
                Password
                Table
                Map
        Passwd
                Filename
DELETE /resolver/(resolver)
    This function deletes an existing resolver. A resolver can not be deleted, if it is contained in a realm
    Parameters
            resolver – the name of the resolver to delete.
    Return
        json with success or fail


        {
  "deflocal": {
    "censor_keys": [],
    "data": ResolverData {
      "filename": "/etc/passwd"
    },
    "resolvername": "deflocal",
    "type": "passwdresolver"
  }
}
*/
@Injectable({
  providedIn: "root"
})
export class ResolverService {
  private readonly resolverBaseUrl = environment.proxyUrl + "/resolver/";
  private readonly authService = inject(AuthService);

  selectedResolverName = signal<string>("");

  constructor() {
    effect(() => {
      const resolvers = this.resolvers();
      console.log("Resolvers changed:", resolvers);
    });

    effect(() => {
      const resolvers = this.resolversResource.value()?.result?.value;
      console.log("Resolvers resource changed:", resolvers);
    });
  }

  postResolverTest() {
    const headers = this.authService.getHeaders();
    return httpResource<PiResponse<any>>({
      url: this.resolverBaseUrl + "test",
      method: "POST",
      headers: headers
    });
  }
  resolversResource = httpResource<PiResponse<any>>({
    url: this.resolverBaseUrl,
    method: "GET",
    headers: this.authService.getHeaders()
  });

  resolvers = computed<Resolver[]>(() => {
    const resolvers = this.resolversResource.value()?.result?.value;
    console.log("Resolvers:", resolvers);
    return resolvers ?? [];
  });

  resolverOptions = computed(() => {
    const resolvers = this.resolversResource.value()?.result?.value;
    return resolvers ? Object.keys(resolvers) : [];
  });

  selectedResolverResource = httpResource<PiResponse<any>>({
    url: this.resolverBaseUrl + this.selectedResolverName(),
    method: "GET",
    headers: this.authService.getHeaders()
  });

  postResolver(resolverName: string, data: any) {
    const headers = this.authService.getHeaders();
    return httpResource<PiResponse<any>>({
      url: this.resolverBaseUrl + resolverName,
      method: "POST",
      body: data,
      headers: headers
    });
  }

  deleteResolver(resolverName: string) {
    const headers = this.authService.getHeaders();
    return httpResource<PiResponse<any>>({
      url: this.resolverBaseUrl + resolverName,
      method: "DELETE",
      headers: headers
    });
  }
}
