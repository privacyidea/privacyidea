import { HttpHeaders } from "@angular/common/http";
import { Injectable } from "@angular/core";
import * as CryptoJS from "crypto-js";
import { environment } from "../../../environments/environment";

export interface LocalServiceInterface {
  key: string;
  bearerTokenKey: string;

  saveData(key: string, value: string): void;

  getData(key: string): string;

  removeData(key: string): void;

  getHeaders(): HttpHeaders;
}

@Injectable({
  providedIn: "root"
})
export class LocalService {
  key = environment.secretAESKey;
  bearerTokenKey = "bearer_token";

  public saveData(key: string, value: string) {
    localStorage.setItem(key, this.encrypt(value));
  }

  public getData(key: string) {
    let data = localStorage.getItem(key) || "";
    return this.decrypt(data);
  }

  public removeData(key: string) {
    localStorage.removeItem(key);
  }

  public getHeaders(): HttpHeaders {
    return new HttpHeaders({
      "PI-Authorization": this.getData("bearer_token") || ""
    });
  }

  private encrypt(txt: string): string {
    return CryptoJS.AES.encrypt(txt, this.key).toString();
  }

  private decrypt(txtToDecrypt: string) {
    return CryptoJS.AES.decrypt(txtToDecrypt, this.key).toString(CryptoJS.enc.Utf8);
  }
}
