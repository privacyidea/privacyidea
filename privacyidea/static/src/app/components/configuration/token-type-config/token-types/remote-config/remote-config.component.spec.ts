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
import { ComponentFixture, TestBed } from "@angular/core/testing";
import { provideRouter } from "@angular/router";
import { RemoteConfigComponent } from "@components/configuration/token-type-config/token-types/remote-config/remote-config.component";
import { REMOTE_SERVER, REMOTE_VERIFY_SSL } from "@constants/token.constants";
import { createTokenTypeConfigForm } from "@testing/token-type-config-form";

describe("RemoteConfigComponent", () => {
  let fixture: ComponentFixture<RemoteConfigComponent>;
  let component: RemoteConfigComponent;
  let configForm: ReturnType<typeof createTokenTypeConfigForm>;

  const flush = async () => {
    fixture.detectChanges();
    await fixture.whenStable();
    fixture.detectChanges();
  };
  const serverInput = () => fixture.nativeElement.querySelector("mat-form-field input") as HTMLInputElement;
  const checkbox = () => fixture.nativeElement.querySelector("input[type=checkbox]") as HTMLInputElement;

  const create = async (config: Record<string, string> = {}) => {
    configForm = createTokenTypeConfigForm(config);
    fixture = TestBed.createComponent(RemoteConfigComponent);
    fixture.componentRef.setInput("config", configForm.form);
    component = fixture.componentInstance;
    await flush();
  };

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [RemoteConfigComponent],
      providers: [provideRouter([])]
    }).compileComponents();
  });

  it("should create", async () => {
    await create();
    expect(component).toBeTruthy();
  });

  it("shows the remote server of the form", async () => {
    await create({ [REMOTE_SERVER]: "https://test.privacyidea.server" });
    expect(serverInput().value).toBe("https://test.privacyidea.server");
  });

  it("writes the typed remote server to the form and keeps the SSL flag", async () => {
    await create({ [REMOTE_VERIFY_SSL]: "True", [REMOTE_SERVER]: "https://old.server.com" });

    serverInput().value = "https://new.server.com";
    serverInput().dispatchEvent(new Event("input"));
    await flush();

    expect(configForm.model().values[REMOTE_SERVER]).toBe("https://new.server.com");
    expect(configForm.model().verifySsl).toBe(true);
    expect(configForm.form.values[REMOTE_SERVER]().dirty()).toBe(true);
  });

  describe("verify SSL checkbox", () => {
    it("is checked for a backend value of True and 1", async () => {
      await create({ [REMOTE_VERIFY_SSL]: "True" });
      expect(checkbox().checked).toBe(true);
      await create({ [REMOTE_VERIFY_SSL]: "1" });
      expect(checkbox().checked).toBe(true);
    });

    it("is unchecked for a backend value of False and 0 and when the backend has none", async () => {
      await create({ [REMOTE_VERIFY_SSL]: "False" });
      expect(checkbox().checked).toBe(false);
      await create({ [REMOTE_VERIFY_SSL]: "0" });
      expect(checkbox().checked).toBe(false);
      await create();
      expect(checkbox().checked).toBe(false);
    });

    it("writes the boolean to the form and marks the field dirty", async () => {
      await create();

      checkbox().click();
      await flush();

      expect(configForm.model().verifySsl).toBe(true);
      expect(configForm.form.verifySsl().dirty()).toBe(true);

      checkbox().click();
      await flush();

      expect(configForm.model().verifySsl).toBe(false);
    });

    it("follows a change of the model", async () => {
      await create();

      configForm.model.update((model) => ({ ...model, verifySsl: true }));
      await flush();

      expect(checkbox().checked).toBe(true);
    });
  });

  it("has no rule that blocks the form", async () => {
    await create();
    expect(configForm.form().valid()).toBe(true);
  });
});
