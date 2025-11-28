/**
 * (c) NetKnights GmbH 2025,  https://netknights.it
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
import { provideHttpClient } from "@angular/common/http";
import { provideHttpClientTesting } from "@angular/common/http/testing";
import { BrowserAnimationsModule } from "@angular/platform-browser/animations";
import { TokenDetailsMachineComponent } from "./token-details-machine.component";
import { MockContainerService, MockMachineService, MockOverflowService } from "../../../../../testing/mock-services";
import { MachineService } from "../../../../services/machine/machine.service";
import { ContentService } from "../../../../services/content/content.service";
import { OverflowService } from "../../../../services/overflow/overflow.service";

describe("TokenDetailsInfoComponent", () => {
  let component: TokenDetailsMachineComponent;
  let fixture: ComponentFixture<TokenDetailsMachineComponent>;

  let machineService: MockMachineService;
  let contentService: MockContainerService;
  let overflowService: MockOverflowService;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [TokenDetailsMachineComponent, BrowserAnimationsModule],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: MachineService, useClass: MockMachineService },
        { provide: ContentService, useValue: MockContainerService },
        { provide: OverflowService, useValue: MockOverflowService }
      ]
    }).compileComponents();

    machineService = TestBed.inject(MachineService) as unknown as MockMachineService;
    contentService = TestBed.inject(ContentService) as unknown as MockContainerService;
    overflowService = TestBed.inject(OverflowService) as unknown as MockOverflowService;

    fixture = TestBed.createComponent(TokenDetailsMachineComponent);
    component = fixture.componentInstance;

    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });
});
