import { Injectable } from "@angular/core";
import * as CryptoJS from "crypto-js";
import { environment } from "../../../environments/environment";

export interface LocalServiceInterface {
  key: string;

  saveData(key: string, value: string): void;

  getData(key: string): string;

  removeData(key: string): void;
}

@Injectable({
  providedIn: "root"
})
export class LocalService implements LocalServiceInterface {
  key = environment.secretAESKey;

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

  private encrypt(txt: string): string {
    return CryptoJS.AES.encrypt(txt, this.key).toString();
  }

  private decrypt(txtToDecrypt: string) {
    return CryptoJS.AES.decrypt(txtToDecrypt, this.key).toString(CryptoJS.enc.Utf8);
  }
}
