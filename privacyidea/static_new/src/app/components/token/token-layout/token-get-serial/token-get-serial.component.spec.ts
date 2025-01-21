import { ComponentFixture, TestBed } from '@angular/core/testing';

import { TokenGetSerial } from './token-get-serial.component';
import { signal } from '@angular/core';

describe('TokenGetSerial', () => {
  let component: TokenGetSerial;
  let fixture: ComponentFixture<TokenGetSerial>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [TokenGetSerial],
    }).compileComponents();

    fixture = TestBed.createComponent(TokenGetSerial);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
