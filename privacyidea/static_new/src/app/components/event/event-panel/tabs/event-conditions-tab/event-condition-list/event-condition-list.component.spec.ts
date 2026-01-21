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

import { EventConditionListComponent } from './event-condition-list.component';
import { EventService } from '../../../../../../services/event/event.service';
import { MockEventService } from "../../../../../../../testing/mock-services/mock-event-service";

describe('EventConditionListComponent', () => {
  let component: EventConditionListComponent;
  let fixture: ComponentFixture<EventConditionListComponent>;
  let mockEventService: MockEventService;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [EventConditionListComponent],
      providers: [
        { provide: EventService, useClass: MockEventService }
      ]
    })
    .compileComponents();

    fixture = TestBed.createComponent(EventConditionListComponent);
    component = fixture.componentInstance;
    mockEventService = TestBed.inject(EventService) as unknown as MockEventService;
    fixture.componentRef.setInput('conditions', { condA: 'valA', condB: 'valB' });
    fixture.componentRef.setInput('action', 'add');
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('should initialize editConditions from input', () => {
    expect(component.editConditions()).toEqual({ condA: 'valA', condB: 'valB' });
  });

  it('should toggle showDescription for a condition', () => {
    expect(component.showDescription['condA']).toBeUndefined();
    component.toggleShowDescription('condA');
    expect(component.showDescription['condA']).toBe(true);
    component.toggleShowDescription('condA');
    expect(component.showDescription['condA']).toBe(false);
  });

  it('should get multi values from string and array', () => {
    expect(component.getMultiValues('a,b,c')).toEqual(['a', 'b', 'c']);
    expect(component.getMultiValues(['x', 'y'])).toEqual(['x', 'y']);
    expect(component.getMultiValues('')).toEqual([]);
  });

  it('should emit newConditionValue on value change if emitOnConditionValueChange is true', () => {
    const emitSpy = jest.fn();
    fixture.componentRef.setInput('emitOnConditionValueChange', true);
    component.newConditionValue = { emit: emitSpy } as any;
    component.onConditionValueChange('condA', 'newVal');
    expect(component.editConditions()['condA']).toBe('newVal');
    expect(emitSpy).toHaveBeenCalledWith({ conditionName: 'condA', conditionValue: 'newVal' });
  });

  it('should not emit newConditionValue if emitOnConditionValueChange is false', () => {
    const emitSpy = jest.fn();
    fixture.componentRef.setInput('emitOnConditionValueChange', false);
    component.newConditionValue = { emit: emitSpy } as any;
    component.onConditionValueChange('condB', 'anotherVal');
    expect(component.editConditions()['condB']).toBe('anotherVal');
    expect(emitSpy).not.toHaveBeenCalled();
  });

  it('should emit actionButtonClicked with correct values', () => {
    const emitSpy = jest.fn();
    component.actionButtonClicked = { emit: emitSpy } as any;
    component.editConditions()['condA'] = 'testVal';
    component.onActionButtonClicked('condA');
    expect(emitSpy).toHaveBeenCalledWith({ conditionName: 'condA', conditionValue: 'testVal' });
  });

  it('should compute availableConditionValues correctly', () => {
    const values = component.availableConditionValues();
    expect(values).toEqual({
      condC: [1, 2, 3],
      condD: ['option1', 'option2']
    });
  });

  it('should set selectedCondition', () => {
    component.selectedCondition.set('condB');
    expect(component.selectedCondition()).toBe('condB');
  });
});
