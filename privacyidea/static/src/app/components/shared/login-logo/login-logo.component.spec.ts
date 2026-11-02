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
import { ConfigService } from "@services/config/config.service";
import { MockConfigService } from "@testing/mock-services/mock-config-service";
import { LoginLogoComponent } from "./login-logo.component";

describe("LoginLogoComponent", () => {
  let fixture: ComponentFixture<LoginLogoComponent>;
  let configService: MockConfigService;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [LoginLogoComponent],
      providers: [{ provide: ConfigService, useClass: MockConfigService }]
    }).compileComponents();
    configService = TestBed.inject(ConfigService) as unknown as MockConfigService;
    fixture = TestBed.createComponent(LoginLogoComponent);
  });

  it("shows the privacyIDEA logo by default", () => {
    fixture.detectChanges();
    const element: HTMLElement = fixture.nativeElement;
    expect(element.querySelector(".logo")).toBeTruthy();
    expect(element.querySelector(".custom-logo")).toBeNull();
  });

  it("shows the configured logo instead", () => {
    configService.config.update((config) => ({ ...config, logo: "custom.png" }));
    fixture.detectChanges();
    const element: HTMLElement = fixture.nativeElement;
    expect(element.querySelector(".custom-logo")).toBeTruthy();
    expect(element.querySelector(".logo")).toBeNull();
  });
});
