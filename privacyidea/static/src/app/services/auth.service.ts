import {Injectable} from '@angular/core';
import {HttpClient, HttpHeaders} from '@angular/common/http';
import {Observable} from 'rxjs';

@Injectable({
  providedIn: 'root'
})
export class AuthService {
  private authUrl = '/auth';

  constructor(private http: HttpClient) {
  }

  authenticate(username: string, password: string, realm: string = ''): Observable<any> {
    const loginData = {
      username, password, realm
    };

    return this.http.post(this.authUrl, JSON.stringify(loginData), {
      headers: new HttpHeaders({
        'Content-Type': 'application/json', 'Accept': 'application/json',
      }), withCredentials: true
    });
  }
}
