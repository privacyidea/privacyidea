import { ComponentFixture, TestBed } from '@angular/core/testing';

import { KeywordFilterComponent } from './keyword-filter.component';
import { signal } from '@angular/core';

describe('KeywordFilterComponent', () => {
  let component: KeywordFilterComponent;
  let fixture: ComponentFixture<KeywordFilterComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [KeywordFilterComponent],
    }).compileComponents();

    fixture = TestBed.createComponent(KeywordFilterComponent);
    component = fixture.componentInstance;
    component.filterHTMLInputElement = document.createElement('input');
    component.filterHTMLInputElement.value = '';
    component.filterValue = signal<Record<string, string>>({});
    component.advancedApiFilter = [];
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
