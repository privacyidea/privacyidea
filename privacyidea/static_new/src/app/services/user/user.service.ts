import {Injectable} from '@angular/core';
import {HttpClient} from '@angular/common/http';
import {LocalService} from '../local/local.service';

@Injectable({
  providedIn: 'root'
})
export class UserService {
  private baseUrl = '/user/';

  constructor(private http: HttpClient, private localService: LocalService) {
  }

  getUsers(userRealm: string) {
    const headers = this.localService.getHeaders();
    return this.http.get(`${this.baseUrl}?realm=${userRealm}`, {headers});
  }
}
