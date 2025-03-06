import { HttpClient, HttpParams } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { Observable } from 'rxjs/internal/Observable';
import { LocalService } from '../local/local.service';
import { environment } from '../../../environments/environment';

interface GetTokenParams {
  serial?: string;
  hostname?: string;
  machineid?: string;
  resolver?: string;
  service_id?: string;
  user?: string;
  count?: string;
  rounds?: string;
  page?: number;
  pageSize?: number;
  sortby?: string;
  sortdir?: string;
  application?: string;
}

@Injectable({
  providedIn: 'root',
})
export class MachineService {
  baseUrl: string = environment.proxyUrl + '/machine/';
  constructor(
    private http: HttpClient,
    private localService: LocalService,
  ) {}

  // POST /machine/tokenoption
  //   This sets a Machine Token option or deletes it, if the value is empty.
  //   Parameters
  //           hostname – identify the machine by the hostname
  //           machineid – identify the machine by the machine ID and the resolver name
  //           resolver – identify the machine by the machine ID and the resolver name
  //           serial – identify the token by the serial number
  //           application – the name of the application like “luks” or “ssh”.
  //           mtid – the ID of the machinetoken definition
  //   Parameters not listed will be treated as additional options.
  //   Return

  postTokenOption(
    hostname: string,
    machineid: string,
    resolver: string,
    serial: string,
    application: string,
    mtid: string,
  ): Observable<any> {
    const headers = this.localService.getHeaders();
    return this.http.post(
      `${this.baseUrl}tokenoption`,
      { hostname, machineid, resolver, serial, application, mtid },
      { headers },
    );
  }

  // GET /machine/authitem/(application)
  // GET /machine/authitem
  //     This fetches the authentication items for a given application and the given client machine.
  //     Parameters: challenge (basestring) – A challenge for which the authentication item is calculated. In case of the Yubikey this can be a challenge that produces a response. The authentication item is the combination of the challenge and the response.
  //                 hostname (basestring) – The hostname of the machine
  //     Return:  dictionary with lists of authentication items
  //     Example response:
  //     HTTP/1.1 200 OK
  //     Content-Type: application/json
  //      {
  //        "id": 1,
  //        "jsonrpc": "2.0",
  //        "result": {
  //          "status": true,
  //          "value": { "ssh": [ { "username": "....",
  //                                "sshkey": "...."
  //                              }
  //                            ],
  //                     "luks": [ { "slot": ".....",
  //                                 "challenge": "...",
  //                                 "response": "...",
  //                                 "partition": "..."
  //                             ]
  //                   }
  //        },
  //        "version": "privacyIDEA unknown"
  //      }

  getAuthItem(
    challenge: string,
    hostname: string,
    application?: string,
  ): Observable<any> {
    const headers = this.localService.getHeaders();
    let params = new HttpParams()
      .set('challenge', challenge)
      .set('hostname', hostname);
    return this.http.get(
      application
        ? `${this.baseUrl}authitem/${application}`
        : `${this.baseUrl}authitem`,
      {
        headers,
        params,
      },
    );
  }

  // POST /machine/token
  //     Attach an existing token to a machine with a certain application.
  //     Parameters
  //             hostname – identify the machine by the hostname
  //             machineid – identify the machine by the machine ID and the resolver name
  //             resolver – identify the machine by the machine ID and the resolver name
  //             serial – identify the token by the serial number
  //             application – the name of the application like “luks” or “ssh”.
  //     Parameters not listed will be treated as additional options.
  //     Return
  //         json result with “result”: true and the machine list in “value”.
  //     Example request:
  //     POST /token HTTP/1.1
  //     Host: example.com
  //     Accept: application/json
  //     { "hostname": "puckel.example.com",
  //       "machienid": "12313098",
  //       "resolver": "machineresolver1",
  //       "serial": "tok123",
  //       "application": "luks" }

  postToken(
    hostname: string,
    machineid: string,
    resolver: string,
    serial: string,
    application: string,
  ): Observable<any> {
    const headers = this.localService.getHeaders();
    return this.http.post(
      `${this.baseUrl}token`,
      { hostname, machineid, resolver, serial, application },
      { headers },
    );
  }

  // GET /machine/token
  //     Return a list of MachineTokens either for a given machine or for a given token.
  //     Parameters
  //             serial – Return the MachineTokens for a the given Token
  //             hostname – Identify the machine by the hostname
  //             machineid – Identify the machine by the machine ID and the resolver name
  //             resolver – Identify the machine by the machine ID and the resolver name
  //             <options> – You can also filter for options like the ‘service_id’ or ‘user’ for SSH applications, or ‘count’ and ‘rounds’ for offline applications. The filter allows the use of “*” to match substrings.
  //     Query Parameters
  //             sortby – sort the output by column. Can be ‘serial’, ‘service_id’…
  //             sortdir – asc/desc
  //             application – The type of application like “ssh” or “offline”.
  //     Return
  //         JSON list of dicts
  //     [{‘application’: ‘ssh’,
  //         ‘id’: 1, ‘options’: {‘service_id’: ‘webserver’,
  //             ‘user’: ‘root’},
  //         ‘resolver’: None, ‘serial’: ‘SSHKEY1’, ‘type’: ‘sshkey’},
  //             … ]

  splitFilters(filterValue: string) {
    var filterMap: { [key: string]: string } = {};
    var regexp = new RegExp(/\w+:\s\w+((?=\s)|$)/, 'g');
    var matches = filterValue.match(regexp);
    console.log('matches', matches);
    if (matches) {
      matches.forEach((match) => {
        var [key, value] = match.split(': ');
        filterMap[key] = value;
      });
    }

    return filterMap;
  }

  getToken(named: {
    sortby?: string;
    sortdir?: string;
    page?: number;
    pageSize: number;
    currentFilter: string;
    application: 'ssh' | 'offline';
  }): Observable<any> {
    const { sortby, sortdir, currentFilter, page, pageSize, application } =
      named;
    var filterMap: { [key: string]: string } = {};
    if (currentFilter) {
      filterMap = this.splitFilters(currentFilter);
    }
    const {
      serial,
      hostname,
      machineid,
      resolver,
      service_id,
      user,
      count,
      rounds,
    } = filterMap;

    const headers = this.localService.getHeaders();
    let params = new HttpParams();
    if (serial) params = params.set('serial', `*${serial}*`);
    if (hostname) params = params.set('hostname', `*${hostname}*`);
    if (machineid) params = params.set('machineid', `*${machineid}*`);
    if (resolver) params = params.set('resolver', `*${resolver}*`);
    if (page) params = params.set('page', page.toString());
    if (pageSize) params = params.set('pagesize', pageSize.toString());
    if (sortby) params = params.set('sortby', sortby);
    if (sortdir) params = params.set('sortdir', sortdir);
    if (application) params = params.set('application', application);
    if (application === 'ssh') {
      if (service_id) params = params.set('service_id', `*${service_id}*`);
      if (user) params = params.set('user', `*${user}*`);
    } else if (application === 'offline') {
      if (count) params = params.set('count', count);
      if (rounds) params = params.set('rounds', rounds);
    }

    return this.http.get(`${this.baseUrl}token`, { headers, params });
  }

  // GET /machine/
  //     List all machines that can be found in the machine resolvers.
  //     Parameters
  //             hostname – only show machines, that match this hostname as substring
  //             ip – only show machines, that exactly match this IP address
  //             id – filter for substring matching ids
  //             resolver – filter for substring matching resolvers
  //             any – filter for a substring either matching in “hostname”, “ip” or “id”
  //     Return
  //         json result with “result”: true and the machine list in “value”.
  //     Example request:
  //     GET /hostname?hostname=on HTTP/1.1
  //     Host: example.com
  //     Accept: application/json
  //     Example response:
  //     HTTP/1.1 200 OK
  //     Content-Type: application/json
  //      {
  //        "id": 1,
  //        "jsonrpc": "2.0",
  //        "result": {
  //          "status": true,
  //          "value": [
  //            {
  //              "id": "908asljdas90ad0",
  //              "hostname": [ "flavon.example.com", "test.example.com" ],
  //              "ip": "1.2.3.4",
  //              "resolver_name": "machineresolver1"
  //            },
  //            {
  //              "id": "1908209x48x2183",
  //              "hostname": [ "london.example.com" ],
  //              "ip": "2.4.5.6",
  //              "resolver_name": "machineresolver1"
  //            }
  //          ]
  //        },
  //        "version": "privacyIDEA unknown"
  //      }

  getMachine(
    hostname: string,
    ip: string,
    id: string,
    resolver: string,
    any: string,
  ): Observable<any> {
    const headers = this.localService.getHeaders();
    let params = new HttpParams()
      .set('hostname', hostname)
      .set('ip', ip)
      .set('id', id)
      .set('resolver', resolver)
      .set('any', any);
    return this.http.get(`${this.baseUrl}`, { headers, params });
  }

  // DELETE /machine/token/(serial)/(machineid)/(resolver)/(application)
  // DELETE /machine/token/(serial)/(application)/(mtid)
  //     Detach a token from a machine with a certain application.
  //     Parameters
  //             machineid – identify the machine by the machine ID and the resolver name
  //             resolver – identify the machine by the machine ID and the resolver name
  //             serial – identify the token by the serial number
  //             application – the name of the application like “luks” or “ssh”.
  //             mtid – the ID of the machinetoken definition
  //     Return
  //         json result with “result”: true and the machine list in “value”.
  //     Example request:
  //     DELETE /token HTTP/1.1
  //     Host: example.com
  //     Accept: application/json
  //     { "hostname": "puckel.example.com",
  //       "resolver": "machineresolver1",
  //       "application": "luks" }

  deleteToken(
    serial: string,
    machineid: string,
    resolver: string,
    application: string,
  ): Observable<any> {
    const headers = this.localService.getHeaders();
    return this.http.delete(
      `${this.baseUrl}token/${serial}/${machineid}/${resolver}/${application}`,
      { headers },
    );
  }

  deleteTokenMtid(
    serial: string,
    application: string,
    mtid: string,
  ): Observable<any> {
    const headers = this.localService.getHeaders();
    return this.http.delete(
      `${this.baseUrl}token/${serial}/${application}/${mtid}`,
      { headers },
    );
  }
}
