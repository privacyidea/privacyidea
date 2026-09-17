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
import { ApiClientService } from "@services/api-client/api-client.service";
import { MockApiClientService } from "@testing/mock-services";
import { ApiClientIssuedKeyBannerComponent } from "./api-client-issued-key-banner.component";

describe("ApiClientIssuedKeyBannerComponent", () => {
  let component: ApiClientIssuedKeyBannerComponent;
  let fixture: ComponentFixture<ApiClientIssuedKeyBannerComponent>;
  let apiClientServiceMock: MockApiClientService;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [ApiClientIssuedKeyBannerComponent],
      providers: [{ provide: ApiClientService, useClass: MockApiClientService }]
    }).compileComponents();

    apiClientServiceMock = TestBed.inject(ApiClientService) as unknown as MockApiClientService;
    fixture = TestBed.createComponent(ApiClientIssuedKeyBannerComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("should render nothing when there is no issued key", () => {
    expect(fixture.nativeElement.querySelector(".issued-key-panel")).toBeNull();
  });

  it("should render the issued key and dismiss it on click", () => {
    apiClientServiceMock.lastIssuedKey.set({ displayName: "My Client", apiKey: "pi_deadbeef_secret" });
    fixture.detectChanges();

    const panel = fixture.nativeElement.querySelector(".issued-key-panel");
    expect(panel).not.toBeNull();
    expect(panel.textContent).toContain("pi_deadbeef_secret");

    const dismissButton: HTMLButtonElement = fixture.nativeElement.querySelector("button[aria-label='Dismiss']");
    dismissButton.click();

    expect(apiClientServiceMock.dismissIssuedKey).toHaveBeenCalled();
  });
});
