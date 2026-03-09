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

import { ComponentFixture, TestBed } from '@angular/core/testing';
import { NO_ERRORS_SCHEMA } from '@angular/core';

import { TokenEnrolledTextComponent } from './token-enrolled-text.component';
import { MockContentService } from 'src/testing/mock-services/mock-content-service';
import { ContentService } from "../../../../services/content/content.service";

describe('TokenEnrolledTextComponent', () => {
  let component: TokenEnrolledTextComponent;
  let fixture: ComponentFixture<TokenEnrolledTextComponent>;
  let mockContentService: MockContentService;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [TokenEnrolledTextComponent],
      providers: [
        { provide: ContentService, useClass: MockContentService }
      ],
      schemas: [NO_ERRORS_SCHEMA]
    }).compileComponents();
    fixture = TestBed.createComponent(TokenEnrolledTextComponent);
    component = fixture.componentInstance;
    mockContentService = TestBed.inject(ContentService) as unknown as MockContentService;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('should emit switchRoute and call contentService.tokenSelected if serial is set', () => {
    const switchRouteSpy = jest.fn();
    fixture.componentRef.setInput("serial", "SERIAL123");
    fixture.detectChanges();
    component.switchRoute.subscribe(switchRouteSpy);
    component.tokenSelected();
    expect(switchRouteSpy).toHaveBeenCalled();
    expect(mockContentService.tokenSelected).toHaveBeenCalledWith('SERIAL123');
  });

  it('should do nothing if serial is not set', () => {
    const switchRouteSpy = jest.fn();
    component.switchRoute.subscribe(switchRouteSpy);
    component.tokenSelected();
    expect(switchRouteSpy).not.toHaveBeenCalled();
    expect(mockContentService.tokenSelected).not.toHaveBeenCalled();
  });

  it('should emit switchRoute and call contentService.containerSelected if containerSerial is set', () => {
    const switchRouteSpy = jest.fn();
    fixture.componentRef.setInput("containerSerial", "CONT123");
    component.switchRoute.subscribe(switchRouteSpy);
    component.containerSelected();
    expect(switchRouteSpy).toHaveBeenCalled();
    expect(mockContentService.containerSelected).toHaveBeenCalledWith('CONT123');
  });

  it('should do nothing if containerSerial is not set', () => {
    const switchRouteSpy = jest.fn();
    component.switchRoute.subscribe(switchRouteSpy);
    component.containerSelected();
    expect(switchRouteSpy).not.toHaveBeenCalled();
    expect(mockContentService.containerSelected).not.toHaveBeenCalled();
  });
});
