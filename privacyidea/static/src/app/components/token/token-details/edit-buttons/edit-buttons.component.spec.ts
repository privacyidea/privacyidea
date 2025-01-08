import {ComponentFixture, TestBed} from '@angular/core/testing';

import {EditButtonsComponent} from './edit-buttons.component';
import {signal} from '@angular/core';

describe('EditButtonsComponent', () => {
  let component: EditButtonsComponent;
  let fixture: ComponentFixture<EditButtonsComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [EditButtonsComponent]
    })
      .compileComponents();

    fixture = TestBed.createComponent(EditButtonsComponent);
    component = fixture.componentInstance;
    component.element = {keyMap: {key: 'value', label: 'label'}};
    component.shouldHide = signal(false);
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
