import {ComponentFixture, TestBed} from '@angular/core/testing';

import {LostTokenComponent} from './lost-token.component';
import {provideHttpClient} from '@angular/common/http';
import {provideHttpClientTesting} from '@angular/common/http/testing';
import {MAT_DIALOG_DATA} from '@angular/material/dialog';

describe('LostTokenComponent', () => {
  let component: LostTokenComponent;
  let fixture: ComponentFixture<LostTokenComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [LostTokenComponent],
      providers: [provideHttpClient(), provideHttpClientTesting(),
        {provide: MAT_DIALOG_DATA, useValue: {
            serial: () => 'mockSerialValue'
          }}]
    })
      .compileComponents();

    fixture = TestBed.createComponent(LostTokenComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
