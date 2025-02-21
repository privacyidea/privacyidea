import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs/internal/Observable';
export class MachineService {
  baseUrl: string = '/machine/';
  constructor(private http: HttpClient) {}
  /**
Parameters
GET /machine/token
    Return a list of MachineTokens either for a given machine or for a given token.
    Parameters
            serial – Return the MachineTokens for a the given Token
            hostname – Identify the machine by the hostname
            machineid – Identify the machine by the machine ID and the resolver name
            resolver – Identify the machine by the machine ID and the resolver name
            <options> – You can also filter for options like the
            ‘service_id’ or ‘user’ for SSH applications,
             or
            ‘count’ and ‘rounds’ for offline applications.
            The filter allows the use of “*” to match substrings.
    Query Parameters
            sortby – sort the output by column. Can be ‘serial’, ‘service_id’…
            sortdir – asc/desc
            application – The type of application like “ssh” or “offline”.
    Return
        JSON list of dicts
    [{‘application’: ‘ssh’,
        ‘id’: 1, ‘options’: {‘service_id’: ‘webserver’,
            ‘user’: ‘root’},
        ‘resolver’: None, ‘serial’: ‘SSHKEY1’, ‘type’: ‘sshkey’},
            … ]
     */
  getMachineToken() // serial: string,
  // hostname: string,
  // machineid: string,
  // resolver: string,
  // options: string,
  // sortby: string,
  // sortdir: string,
  // application: string,
  : Observable<any> {
    return this.http.get('${baseUrl}token', {
      params: {
        // serial: serial,
        // hostname: hostname,
        // machineid: machineid,
        // resolver: resolver,
        // options: options,
        // sortby: sortby,
        // sortdir: sortdir,
        // application: application,
      },
    });
  }
}
