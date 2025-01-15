import {Injectable} from '@angular/core';

@Injectable({
  providedIn: 'root'
})
export class VersionService {
  private readonly version: string;

  constructor() {
    // TODO get version from an environment variable or API
    this.version = '3.12';
  }

  getVersion(): string {
    return this.version;
  }
}
