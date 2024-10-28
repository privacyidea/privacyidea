import {Injectable} from '@angular/core';
import {HttpClient, HttpHeaders} from '@angular/common/http';
import {Observable, throwError} from 'rxjs';
import {catchError, map} from 'rxjs/operators';
import {LocalService} from '../local/local.service';

@Injectable({
  providedIn: 'root'
})
export class ContainerService {
  private baseUrl = 'http://127.0.0.1:5000/container';

  constructor(private http: HttpClient, private localStore: LocalService) {
  }

  getContainerData(): Observable<any> {
    const headers = new HttpHeaders({
      'PI-Authorization': this.localStore.getData('bearer_token') || ''
    });

    return this.http.get<any>(this.baseUrl, {headers}).pipe(
      map(response => response.result.value.containers),
      catchError(error => {
        console.error('Failed to get container data', error);
        return throwError(error);
      })
    );
  }
}
