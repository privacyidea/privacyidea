/**
 * (c) NetKnights GmbH 2026,  https://netknights.it
 *
 * This code is free software; you can redistribute it and/or
 * modify it under the terms of the GNU AFFERO GENERAL PUBLIC LICENSE
 * as published by the Free Software Foundation; either
 * version 3 of the License, or any later version.
 *
 * This code is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
 * GNU AFFERO GENERAL PUBLIC LICENSE for more details.
 *
 * You should have received a copy of the GNU Affero General Public
 * License along with this program.  If not, see <http://www.gnu.org/licenses/>.
 *
 * SPDX-License-Identifier: AGPL-3.0-or-later
 **/
import { inject, Injectable } from "@angular/core";
import { environment } from "@env/environment";
import {
  AuthSessionModeService,
  AuthSessionModeServiceInterface
} from "@services/auth-session-mode/auth-session-mode.service";
import * as CryptoJS from "crypto-js";

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

  private readonly authSessionModeService: AuthSessionModeServiceInterface = inject(AuthSessionModeService);

  public saveData(key: string, value: string) {
    this.storage().setItem(key, this.encrypt(value));
  }

  public getData(key: string) {
    const data = this.storage().getItem(key) || "";
    return this.decrypt(data);
  }

  public removeData(key: string) {
    this.storage().removeItem(key);
  }

  private storage(): Storage {
    return this.authSessionModeService.storage();
  }

  private encrypt(txt: string): string {
    return CryptoJS.AES.encrypt(txt, this.key).toString();
  }

  private decrypt(txtToDecrypt: string) {
    return CryptoJS.AES.decrypt(txtToDecrypt, this.key).toString(CryptoJS.enc.Utf8);
  }
}
