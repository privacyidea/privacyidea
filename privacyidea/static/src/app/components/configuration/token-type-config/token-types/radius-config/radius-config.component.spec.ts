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
import { MatSelect } from "@angular/material/select";
import { By } from "@angular/platform-browser";
import { provideRouter } from "@angular/router";
import { RadiusConfigComponent } from "@components/configuration/token-type-config/token-types/radius-config/radius-config.component";
import { RADIUS_SERVER } from "@constants/token.constants";
import { createTokenTypeConfigForm } from "@testing/token-type-config-form";

const mockRadiusServers = ["radius-server-1", "radius-server-2", "radius-server-3"];

describe("RadiusConfigComponent", () => {
  let fixture: ComponentFixture<RadiusConfigComponent>;
  let component: RadiusConfigComponent;
  let configForm: ReturnType<typeof createTokenTypeConfigForm>;

  const flush = async () => {
    fixture.detectChanges();
    await fixture.whenStable();
    fixture.detectChanges();
  };
  const textInput = () => fixture.nativeElement.querySelector("mat-form-field input") as HTMLInputElement;

  const create = async (config: Record<string, string> = {}, listable = true) => {
    configForm = createTokenTypeConfigForm(config);
    fixture = TestBed.createComponent(RadiusConfigComponent);
    fixture.componentRef.setInput("config", configForm.form);
    fixture.componentRef.setInput("radiusServers", mockRadiusServers);
    fixture.componentRef.setInput("radiusServersListable", listable);
    component = fixture.componentInstance;
    await flush();
  };

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [RadiusConfigComponent],
      providers: [provideRouter([])]
    }).compileComponents();
  });

  afterEach(() => {
    document.querySelectorAll(".cdk-overlay-container").forEach((container) => (container.innerHTML = ""));
  });

  it("should create", async () => {
    await create();
    expect(component).toBeTruthy();
  });

  it("should offer the configured RADIUS servers in a select when they can be listed", async () => {
    await create();
    const element: HTMLElement = fixture.nativeElement;
    expect(element.querySelector("mat-select")).not.toBeNull();
    expect(element.querySelector("mat-hint")?.textContent).toContain("Select a predefined");
    expect(element.textContent).not.toContain("enrollRADIUS");
  });

  it("writes the picked RADIUS server to the form", async () => {
    await create();
    const select = fixture.debugElement.query(By.directive(MatSelect)).componentInstance as MatSelect;
    select.open();
    await flush();

    (document.querySelectorAll("mat-option")[1] as HTMLElement).click();
    await flush();

    expect(configForm.model().values[RADIUS_SERVER]).toBe("radius-server-2");
    expect(configForm.form.values[RADIUS_SERVER]().dirty()).toBe(true);
  });

  it("shows the RADIUS server of the form in the select", async () => {
    await create({ [RADIUS_SERVER]: "radius-server-3" });
    expect((fixture.debugElement.query(By.directive(MatSelect)).componentInstance as MatSelect).value).toBe(
      "radius-server-3"
    );
  });

  it("clears the RADIUS server through the form and marks the field dirty", async () => {
    await create({ [RADIUS_SERVER]: "radius-server-1" });

    fixture.debugElement.query(By.css("app-clear-button button")).nativeElement.click();
    await flush();

    expect(configForm.model().values[RADIUS_SERVER]).toBe("");
    expect(configForm.form.values[RADIUS_SERVER]().dirty()).toBe(true);
  });

  describe("when the RADIUS servers cannot be listed", () => {
    beforeEach(async () => {
      await create({ [RADIUS_SERVER]: "radius-server-1" }, false);
    });

    it("should replace the select by a text input naming the missing right", () => {
      const element: HTMLElement = fixture.nativeElement;
      expect(element.querySelector("mat-select")).toBeNull();
      expect(element.querySelector("mat-hint")?.textContent).toContain("enrollRADIUS");
    });

    it("should show the configured value and write the typed one to the form", async () => {
      expect(textInput().value).toBe("radius-server-1");

      textInput().value = "radius-server-9";
      textInput().dispatchEvent(new Event("input"));
      await flush();

      expect(configForm.model().values[RADIUS_SERVER]).toBe("radius-server-9");
    });

    it("clears the typed value through the clear button", async () => {
      fixture.debugElement.query(By.css("app-clear-button button")).nativeElement.click();
      await flush();

      expect(textInput().value).toBe("");
      expect(configForm.model().values[RADIUS_SERVER]).toBe("");
    });
  });

  it("should handle radiusServers input correctly", async () => {
    await create();
    expect(component.radiusServers()).toEqual(mockRadiusServers);
    expect(component.radiusServers().length).toBe(3);
  });

  it("should handle empty radiusServers array", async () => {
    await create();
    fixture.componentRef.setInput("radiusServers", []);
    fixture.detectChanges();
    expect(component.radiusServers()).toEqual([]);
    expect(component.radiusServers().length).toBe(0);
  });

  it("should handle expanded input", async () => {
    await create();
    fixture.componentRef.setInput("expanded", true);
    fixture.detectChanges();
    expect(component.expanded()).toBe(true);

    fixture.componentRef.setInput("expanded", false);
    fixture.detectChanges();
    expect(component.expanded()).toBe(false);
  });
});
