import {Injectable} from '@angular/core';
import {Observable} from 'rxjs';
import {LocalService} from '../local/local.service';
import {HttpClient} from '@angular/common/http';

@Injectable({
  providedIn: 'root'
})
export class RealmService {

  constructor(private http: HttpClient,
              private localService: LocalService) {
  }


  getRealms(): Observable<any> {
    const headers = this.localService.getHeaders();
    return this.http.get('/realm', {headers})
  }

  getDefaultRealm() {
    const headers = this.localService.getHeaders();
    return this.http.get('/defaultrealm', {headers})
  }
}
